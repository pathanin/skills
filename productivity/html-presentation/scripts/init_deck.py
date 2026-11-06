# -*- coding: utf-8 -*-
"""Create an HTML deck folder, either from an existing .pptx or from the starter.

    python init_deck.py DECK --from SOURCE.pptx [--font FAMILY] [--lang th] [--title "..."]
    python init_deck.py DECK --new [--font FAMILY] [--lang th] [--title "..."]

Writes DECK/ (index.html, deck.css, deck.js, review.js, fonts/, media/, review.json, deck.json,
.source/), and in the current directory a review launcher (review.cmd on Windows, review.command on
macOS, review.sh elsewhere) and a marked section in
CLAUDE.md so later sessions know the review loop and export commands without loading the skill.
Refuses to touch an existing DECK/index.html (it is the source of truth once created).
"""
import argparse
import datetime
import html
import json
import os
import shlex
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
import fonts  # noqa: E402

MARK_A, MARK_B = "<!-- html-presentation:start -->", "<!-- html-presentation:end -->"
WIN = sys.platform == "win32"
PY = "python" if WIN else "python3"          # stock macOS has only python3
# double-clickable launcher: .cmd in Explorer, .command in Finder
LAUNCHER_EXT = ".cmd" if WIN else ".command" if sys.platform == "darwin" else ".sh"
# fallbacks for a new deck when the default family is not installed (macOS has no Aptos without Office)
FALLBACK = {"en": ["Aptos", "Arial"], "th": ["IBM Plex Sans Thai", "Noto Sans Thai", "Leelawadee UI", "Tahoma"]}
# (not Thonburi / Sukhumvit Set: see fonts.aat_only)


def font_css(family, files):
    out = []
    for w, key in ((400, "regular"), (700, "bold")):
        if key in files:
            fmt = "opentype" if files[key].endswith(".otf") else "truetype"
            out.append(f'@font-face{{font-family:"DeckFont";src:url("fonts/{files[key]}") format("{fmt}");font-weight:{w};font-display:block}}')
        else:
            out.append(f'@font-face{{font-family:"DeckFont";src:local("{family}");font-weight:{w}}}')
    return "\n".join(out) + "\n"


def page(title, lang, sections):
    return (f'<!doctype html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>{html.escape(title)}</title>\n<link rel="stylesheet" href="deck.css">\n</head>\n<body>\n'
            f'<div class="stage">\n' + "\n".join(sections) + '\n</div>\n<div id="hud"></div><pre id="qa"></pre>\n'
            f'<script src="deck.js"></script>\n<script src="review.js"></script>\n</body>\n</html>\n')


def write_launcher(path, rel):
    server = (HERE / "review_server.mjs").as_posix()
    if WIN:
        q = lambda v: '"' + v.replace("%", "%%") + '"'
        text = f'@echo off\r\ncd /d "%~dp0"\r\nnode {q(server)} {q(rel)} --open\r\n'
    else:
        # Finder starts .command files with a minimal PATH, so fall back to the node found now
        node = shutil.which("node") or "node"
        text = (f'#!/bin/bash\ncd "$(dirname "$0")"\nNODE="$(command -v node || echo {shlex.quote(node)})"\n'
                f'exec "$NODE" {shlex.quote(server)} {shlex.quote(rel)} --open\n')
    with open(path, "w", encoding="utf-8", newline="") as f:     # keep the line endings exactly as written
        f.write(text)
    if not WIN: path.chmod(0o755)


def claude_md(deck_rel, deck_abs, source, launcher):
    s = SKILL.as_posix()
    src_note = ("Slides carry `data-src` (source slide number) and shapes `data-id`, so the export can replay edits onto "
                f"`{deck_rel}/.source/source.pptx`. Keep those attributes when editing; a copied slide or shape drops `data-id`/`data-src` "
                "or keeps them only on the original.") if source else \
               "The deck was started from the skill's starter (no source PPTX): the export builds every shape from the HTML."
    return f"""{MARK_A}
## HTML deck (html-presentation skill)

`{deck_rel}/index.html` is the source of truth. Present it by opening it in a browser
(→/Space next, ←/PgUp back, f or Enter fullscreen). Skill scripts live in `{s}/scripts`.
{src_note}

**Review loop.** The user runs `{launcher}` (localhost server); in the browser **E** edits text,
**C** drops a comment pin, **H** hides pins. Everything autosaves to `{deck_rel}/review.json`.
At the start of every task here, check that file. If it has edits or open comments:
1. `{PY} "{s}/scripts/apply_review.py" "{deck_rel}"` (dry run), then add `--write`. An edit applies only if the box still has its `before` text.
2. Handle each open comment in index.html, then set `"done": true` and a short `"reply"` on it (the user's language). Never delete comments.
3. Check: `node "{s}/scripts/shoot.mjs" "{deck_rel}" OUTDIR N,M` (screenshots) and `--qa` (overflow + fonts); look at every slide you touched.

**Editing rules.** Keep the element vocabulary in `{s}/references/format.md` (absolutely positioned
`.sh/.tx/.pic/.tbl` with inline styles; no per-element animation markup). After deleting or reordering
slides run `{PY} "{s}/scripts/deck_tool.py" renumber "{deck_rel}"`.

**Export (only when asked):** `{PY} "{s}/scripts/export.py" "{deck_rel}" --pptx OUT.pptx --pdf OUT.pdf`
(on Windows with PowerPoint installed it adds the entrance animations and embeds fonts; elsewhere the PPTX has no animation; `--no-anim` skips that). Exports are outputs; never edit them by hand.
{MARK_B}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--from", dest="src")
    g.add_argument("--new", action="store_true")
    ap.add_argument("--font")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--title")
    ap.add_argument("--no-project-files", action="store_true", help="skip the review launcher and the CLAUDE.md section")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    deck = Path(a.deck).resolve()
    if (deck / "index.html").exists():
        sys.exit(f"{deck / 'index.html'} exists and is the source of truth. Not overwriting.")
    deck.mkdir(parents=True, exist_ok=True)
    for d in ("fonts", "media", ".source"): (deck / d).mkdir(exist_ok=True)

    info = {}
    if a.src:
        import convert_pptx
        src = Path(a.src).resolve()
        d0 = convert_pptx.Deck(str(src), str(deck))
        heading, body = d0.fonts()
        family = a.font or d0.dominant_font() or body or heading or "Arial"
        if abs(d0.size[0] / d0.size[1] - 16 / 9) > 0.01:
            print(f"!! source slides are {d0.size[0] / d0.size[1]:.2f}:1, not 16:9; the 1280x720 HTML stage stretches them")
    else:
        family = a.font or ("IBM Plex Sans Thai" if a.lang.startswith("th") else "Aptos")
    found = fonts.find(family)
    if not found and not a.font and not a.src:
        for alt in FALLBACK["th" if a.lang.startswith("th") else "en"]:
            if alt != family and (found := fonts.find(alt)):
                print(f"font '{family}' is not installed; using '{alt}' (pass --font to choose)")
                family = alt
                break
    files = {k: fonts.bundle(face, deck / "fonts") for k, face in found.items()}
    if a.lang.startswith("th") and any(fonts.aat_only(face) for face in found.values()):
        print(f"!! '{family}' shapes text only with Apple AAT tables, which browsers drop from bundled fonts: "
              "Thai and other complex scripts will break (dotted circles). Pick another family with --font.")
    ln = fonts.line_normal(found["regular"]) if "regular" in found else 1.2
    if not found: print(f"!! font '{family}' not found on this machine: the deck uses local() and the QA font check will say false")

    if a.src:
        sections, info = convert_pptx.convert(str(src), str(deck), lang=a.lang, line_normal=ln)
        title = a.title or src.stem
        shutil.copy(src, deck / ".source" / "source.pptx")
    else:
        starter = (SKILL / "assets" / "starter.html").read_text(encoding="utf-8")
        sections = [starter.strip()]
        title = a.title or "Presentation"

    doc = page(title, a.lang, sections)
    (deck / "index.html").write_text(doc, encoding="utf-8", newline="\n")
    if a.src: (deck / ".source" / "baseline.html").write_text(doc, encoding="utf-8", newline="\n")
    css = (SKILL / "assets" / "runtime" / "deck.css").read_text(encoding="utf-8")
    (deck / "deck.css").write_text(font_css(family, files) + css, encoding="utf-8", newline="\n")
    for f in ("deck.js", "review.js"):
        shutil.copy(SKILL / "assets" / "runtime" / f, deck / f)
    if not (deck / "review.json").exists():
        (deck / "review.json").write_text('{\n  "edits": {},\n  "comments": []\n}\n', encoding="utf-8")
    meta = {"title": title, "lang": a.lang, "font": {"family": family, "files": files, "line_normal": ln},
            "source": ".source/source.pptx" if a.src else None, "created": datetime.date.today().isoformat()}
    if a.src: meta["source_size_emu"] = info["size"]
    (deck / "deck.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not a.no_project_files:
        root = Path.cwd()
        try: rel = deck.relative_to(root).as_posix()
        except ValueError: rel = deck.as_posix()
        names = [f"review{LAUNCHER_EXT}", f"review-{deck.name}{LAUNCHER_EXT}"] + \
                [f"review-{deck.name}-{k}{LAUNCHER_EXT}" for k in range(2, 100)]
        # reuse the launcher that already points at this deck, else the first free name
        launcher = next(root / n for n in names if not (root / n).exists()
                        or rel in (root / n).read_text(encoding="utf-8", errors="ignore"))
        write_launcher(launcher, rel)
        md = root / "CLAUDE.md"
        cur = md.read_text(encoding="utf-8") if md.exists() else "# CLAUDE.md\n"
        block = claude_md(rel, deck, bool(a.src), launcher.name)
        if MARK_A in cur:
            pre, rest = cur.split(MARK_A, 1)
            cur = pre + block.strip() + rest.split(MARK_B, 1)[1] if MARK_B in rest else pre + block
        else:
            cur = cur.rstrip() + "\n\n" + block
        md.write_text(cur, encoding="utf-8", newline="\n")
        print(f"wrote {launcher.name} and the html-presentation section of CLAUDE.md")
    n = info.get("slides", doc.count('class="slide"'))
    print(f"deck: {deck}  ({n} slides, font {family}{' bundled' if files else ' NOT bundled'}, line-height normal {ln})")
    if a.src: print(f"media: {info['media']} files; source kept as .source/source.pptx, baseline as .source/baseline.html")


if __name__ == "__main__":
    main()
