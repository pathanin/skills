# -*- coding: utf-8 -*-
"""Create an HTML deck folder, either from an existing .pptx or from the starter.

    python init_deck.py DECK --from SOURCE.pptx [--font FAMILY] [--lang th] [--title "..."]
    python init_deck.py DECK --new [--font FAMILY] [--lang th] [--title "..."]

Writes DECK/ (index.html, deck.css, deck.js, review.js, fonts/, media/, review.json, deck.json,
.source/), and in the current directory a review launcher (review.cmd) and a marked section in
CLAUDE.md so later sessions know the review loop and export commands without loading the skill.
Refuses to touch an existing DECK/index.html (it is the source of truth once created).
"""
import argparse
import datetime
import html
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
import fonts  # noqa: E402

MARK_A, MARK_B = "<!-- html-presentation:start -->", "<!-- html-presentation:end -->"


def font_css(family, files):
    out = []
    for w, key in ((400, "regular"), (700, "bold")):
        if key in files:
            out.append(f'@font-face{{font-family:"DeckFont";src:url(fonts/{files[key]}) format("truetype");font-weight:{w};font-display:block}}')
        else:
            out.append(f'@font-face{{font-family:"DeckFont";src:local("{family}");font-weight:{w}}}')
    return "\n".join(out) + "\n"


def page(title, lang, sections):
    return (f'<!doctype html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>{html.escape(title)}</title>\n<link rel="stylesheet" href="deck.css">\n</head>\n<body>\n'
            f'<div class="stage">\n' + "\n".join(sections) + '\n</div>\n<div id="hud"></div><pre id="qa"></pre>\n'
            f'<script src="deck.js"></script>\n<script src="review.js"></script>\n</body>\n</html>\n')


def claude_md(deck_rel, deck_abs, source):
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

**Review loop.** The user runs `review.cmd` (localhost server); in the browser **E** edits text,
**C** drops a comment pin, **H** hides pins. Everything autosaves to `{deck_rel}/review.json`.
At the start of every task here, check that file. If it has edits or open comments:
1. `python "{s}/scripts/apply_review.py" "{deck_rel}"` (dry run), then add `--write`. An edit applies only if the box still has its `before` text.
2. Handle each open comment in index.html, then set `"done": true` and a short `"reply"` on it (the user's language). Never delete comments.
3. Check: `node "{s}/scripts/shoot.mjs" "{deck_rel}" OUTDIR N,M` (screenshots) and `--qa` (overflow + fonts); look at every slide you touched.

**Editing rules.** Keep the element vocabulary in `{s}/references/format.md` (absolutely positioned
`.sh/.tx/.pic/.tbl` with inline styles; no per-element animation markup). After deleting or reordering
slides run `python "{s}/scripts/deck_tool.py" renumber "{deck_rel}"`.

**Export (only when asked):** `python "{s}/scripts/export.py" "{deck_rel}" --pptx OUT.pptx --pdf OUT.pdf`
(PowerPoint adds the animations if installed; `--no-anim` skips that). Exports are outputs; never edit them by hand.
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
    ap.add_argument("--no-project-files", action="store_true", help="skip review.cmd and the CLAUDE.md section")
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
    files = {}
    for k, p in found.items():
        files[k] = p.name
        shutil.copy(p, deck / "fonts" / p.name)
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
        launcher = root / "review.cmd"
        if launcher.exists() and rel not in launcher.read_text(encoding="utf-8", errors="ignore"):
            launcher = root / f"review-{deck.name}.cmd"
        launcher.write_text(f'@echo off\r\ncd /d "%~dp0"\r\nnode "{(HERE / "review_server.mjs").as_posix()}" "{rel}" --open\r\n', encoding="utf-8")
        md = root / "CLAUDE.md"
        cur = md.read_text(encoding="utf-8") if md.exists() else "# CLAUDE.md\n"
        block = claude_md(rel, deck, bool(a.src))
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
