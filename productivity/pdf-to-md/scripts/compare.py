"""Check markdown coverage against the source PDF.

Builds a token multiset from the PDF pages and from the markdown, then reports
tokens missing from the markdown (hard failure) and extra tokens (soft — merged
cells are duplicated on purpose).

Usage:
    python compare.py <pdf> <md> [--pages 5-10]
"""

import argparse
import re
import sys
from collections import Counter

import fitz

TOKEN = re.compile(r"[^\s|]+")


def normalise(text):
    text = text.replace("–", "-").replace("—", "-").replace("’", "'")
    text = text.replace("_", " ")  # extraction modes disagree on underscores
    return text


def tokens(text):
    text = normalise(text)
    return Counter(t for t in TOKEN.findall(text) if t.strip("-*#|—"))


def pdf_tokens(doc, pages):
    per_page = {}
    for p in pages:
        per_page[p + 1] = tokens(doc[p].get_text())
    return per_page


def md_tokens(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"^[#>\s]*", "", text, flags=re.M)
    return tokens(text)


def parse_pages(spec, n):
    if not spec:
        return list(range(n))
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a) - 1, int(b)))
        else:
            out.append(int(part) - 1)
    return [p for p in out if 0 <= p < n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("md")
    ap.add_argument("--pages")
    a = ap.parse_args()

    doc = fitz.open(a.pdf)
    pages = parse_pages(a.pages, doc.page_count)
    per_page = pdf_tokens(doc, pages)
    have = md_tokens(a.md)

    total_missing = 0
    for pno, want in sorted(per_page.items()):
        missing = want - have
        if missing:
            total_missing += sum(missing.values())
            print(f"page {pno}: MISSING {sum(missing.values())}")
            for tok, n in missing.most_common(40):
                print(f"    {n}x {tok!r}")

    all_pdf = Counter()
    for c in per_page.values():
        all_pdf.update(c)
    extra = have - all_pdf
    print(f"\nmissing tokens: {total_missing}")
    print(f"extra tokens:   {sum(extra.values())} (duplicated merged cells expected)")
    if extra:
        for tok, n in extra.most_common(15):
            print(f"    {n}x {tok!r}")
    sys.exit(1 if total_missing else 0)


if __name__ == "__main__":
    main()
