"""Fold the reviewer's text edits from DECK/review.json into DECK/index.html.

    python apply_review.py DECK            # dry run: list what would change
    python apply_review.py DECK --write    # apply, then drop the applied edits from review.json

Each edit carries the box's text before the change; an edit is applied only if index.html still
has exactly that text, so nothing is overwritten blindly. Comments are left alone (Claude answers
them by setting "reply" and "done" on each comment).
"""
import html as H
import json
import re
import sys
from pathlib import Path



def text_of(inner):
    """Approximate the browser's innerText for one .tx/.cell: paragraphs joined by newlines."""
    paras = re.findall(r"<p[^>]*>(.*?)</p>", inner, flags=re.S)
    return "\n".join(H.unescape(re.sub(r"<[^>]+>", "", p)) for p in paras).replace(" ", " ").strip()


def norm(s):
    return re.sub(r"\s+", "", s)   # browser innerText and index.html differ in paragraph breaks


def locate(doc, key):
    """(start, end) of the inner HTML of the text box named by key 'sN|Shape name[#cell]'."""
    sid, rest = key.split("|", 1)
    name, _, cell = rest.partition("#")
    sec = re.search(rf'<section class="slide" id="{sid}"[ >].*?</section>', doc, flags=re.S)
    if not sec:
        return None
    tag = f'data-name="{H.escape(name, quote=True)}"'
    i = doc.find(tag, sec.start(), sec.end())
    if i < 0:
        return None
    if cell:
        pos = i
        for _ in range(int(cell) + 1):
            pos = doc.find('<div class="cell"', pos + 1, sec.end())
            if pos < 0:
                return None
        m = re.compile(r'<div class="cell"[^>]*>(.*?)</div>', re.S).match(doc, pos)
    else:
        m = re.compile(r'<div class="tx"[^>]*>(.*?)</div>', re.S).search(doc, i, sec.end())
    return (m.start(1), m.end(1)) if m else None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args: sys.exit("usage: python apply_review.py DECK [--write]")
    root = Path(args[0])
    INDEX, REVIEW = root / "index.html", root / "review.json"
    write = "--write" in sys.argv
    doc = INDEX.read_text(encoding="utf-8")
    rv = json.loads(REVIEW.read_text(encoding="utf-8"))
    applied, problems = [], []
    for key, e in rv.get("edits", {}).items():
        span = locate(doc, key)
        if not span:
            problems.append(f"{key}: box not found")
            continue
        cur = text_of(doc[span[0]:span[1]])
        if norm(cur) == norm(e["after"]):
            applied.append(key)            # already in index.html
            continue
        if norm(cur) != norm(e["before"]):
            problems.append(f"{key}: index.html text changed since the edit, skipped\n    now:  {cur[:80]}\n    was:  {e['before'][:80]}")
            continue
        new = e["html"].replace("<br>", "\n")
        if "<script" in new.lower() or "<div" in new.lower():
            problems.append(f"{key}: unexpected markup in edit, skipped")
            continue
        doc = doc[:span[0]] + new + doc[span[1]:]
        applied.append(key)
        a, b = norm(e["before"]), norm(e["after"])
        k = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        cut = max(0, k - 40)
        print(f"s{e['slide']} [{e['name']}]\n    - …{a[cut:cut + 120]}\n    + …{b[cut:cut + 120]}")
    for p in problems:
        print("!!", p)
    if write:
        INDEX.write_text(doc, encoding="utf-8", newline="")
        for k in applied:
            rv["edits"].pop(k, None)
        REVIEW.write_text(json.dumps(rv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(applied)} applied{'' if write else ' (dry run)'}, {len(problems)} skipped, "
          f"{sum(1 for c in rv.get('comments', []) if not c.get('done'))} open comments")


if __name__ == "__main__":
    main()
