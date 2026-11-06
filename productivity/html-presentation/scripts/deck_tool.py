# -*- coding: utf-8 -*-
"""Small maintenance commands for an HTML deck.

    python deck_tool.py list DECK          # slide number, id, source slide, title, shape count
    python deck_tool.py renumber DECK      # after deleting/reordering slides: ids become s1..sN in order,
                                           # and review.json comments/edits follow their slides
"""
import json
import re
import sys
from pathlib import Path

SEC = re.compile(r'<section class="slide" id="(s\d+)"')


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3 or sys.argv[1] not in ("list", "renumber"): sys.exit(__doc__)
    deck = Path(sys.argv[2])
    idx = deck / "index.html"
    doc = idx.read_text(encoding="utf-8")
    ids = SEC.findall(doc)
    if sys.argv[1] == "list":
        for k, m in enumerate(re.finditer(r'<section class="slide"([^>]*)>(.*?)</section>', doc, flags=re.S), 1):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
            n = len(re.findall(r'data-name="', m.group(2)))
            print(f"{k:>3}  {attrs.get('id', ''):<5} src={attrs.get('data-src', '-'):<4} {n:>3} shapes  {attrs.get('data-title', '')}")
        return
    old2new = {}
    counter = iter(range(1, len(ids) + 1))

    def rep(m):
        new = f"s{next(counter)}"
        old2new.setdefault(m.group(1), new)
        return f'<section class="slide" id="{new}"'
    doc2 = SEC.sub(rep, doc)
    if len(set(ids)) != len(ids): print("!! duplicate slide ids found; comments on the duplicates follow the first one")
    idx.write_text(doc2, encoding="utf-8", newline="")
    rv = deck / "review.json"
    if rv.exists():
        data = json.loads(rv.read_text(encoding="utf-8"))
        num = {int(o[1:]): int(n[1:]) for o, n in old2new.items()}
        for c in data.get("comments", []):
            if c.get("slide") in num: c["slide"] = num[c["slide"]]
            elif c.get("slide") is not None and not c.get("done"):
                print(f"!! open comment on removed slide {c['slide']}: {c.get('text', '')[:60]}")
        edits = {}
        for k, e in data.get("edits", {}).items():
            sid, rest = k.split("|", 1)
            if sid in old2new:
                e["slide"] = int(old2new[sid][1:]); edits[f"{old2new[sid]}|{rest}"] = e
            else:
                print(f"!! pending edit on removed slide {sid}: {rest}")
        data["edits"] = edits
        rv.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    moved = sum(1 for k, o in enumerate(ids, 1) if o != f"s{k}")
    print(f"{len(ids)} slides, {moved} renumbered")


if __name__ == "__main__":
    main()
