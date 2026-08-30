"""Shape pdf2md output into a section file, without retyping any value.

Drops page markers and page numbers, rejoins a table split across pages,
merges a two-level header into one row, and promotes headings you name.

Usage:
    python shape.py in.md out.md
        [--start "^2\\. TFEX"] [--stop "^3\\. Equity"]
        [--heading "^Project plan$=>## Project plan"] ...
"""

import argparse
import re


def cells_of(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def merge_two_level(block):
    """| A |  | B |  | over | C | D | C | D |  ->  one header row."""
    if len(block) < 4:
        return block
    head, sub = cells_of(block[0]), cells_of(block[2])
    if "" not in head or "" in sub or len(head) != len(sub):
        return block
    filled, last = [], ""
    for cell in head:
        last = cell or last
        filled.append(last)
    combined = [f"{a} — {b}" if a and b else (a or b) for a, b in zip(filled, sub)]
    return ["| " + " | ".join(combined) + " |", block[1]] + block[3:]


def is_separator(line):
    return "-" in line and set(line) <= set("|- ")


def join_split_tables(lines):
    """A table continued on the next page repeats its header: drop the repeat."""
    out, last_header, sub_row = [], None, None
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if line.startswith("|") and is_separator(nxt):
            tail = [l for l in out[::-1] if l.strip()]
            if line == last_header and tail and tail[0].startswith("|"):
                i += 2
                if i < len(lines) and lines[i] == sub_row:
                    i += 1  # its repeated second-level header row
                while out and not out[-1].strip():
                    out.pop()
                continue
            last_header = line
            sub_row = lines[i + 2] if i + 2 < len(lines) else None
        out.append(line)
        i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--start", help="regex of the first line to keep")
    ap.add_argument("--stop", help="regex of the first line to drop")
    ap.add_argument("--heading", action="append", default=[],
                    help='"<regex>=>​<replacement>", repeatable')
    a = ap.parse_args()

    with open(a.src, encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f]

    for spec, keep_from in ((a.start, True), (a.stop, False)):
        if not spec:
            continue
        for i, line in enumerate(lines):
            if re.match(spec, line):
                lines = lines[i:] if keep_from else lines[:i]
                break

    lines = [l for l in lines
             if not re.fullmatch(r"<!-- page \d+ -->", l)
             and not re.fullmatch(r"\d{1,3}", l.strip())]
    lines = join_split_tables(lines)

    kept, block = [], []
    for line in lines:
        if line.startswith("|"):
            block.append(line)
            continue
        if block:
            kept.extend(merge_two_level(block))
            block = []
        kept.append(line)
    if block:
        kept.extend(merge_two_level(block))

    text = "\n".join(kept)
    for spec in a.heading:
        pattern, _, repl = spec.partition("=>")
        text = re.sub(pattern, repl.replace("\\n", "\n"), text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
