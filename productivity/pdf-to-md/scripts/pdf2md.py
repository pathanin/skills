"""Convert a PDF to markdown with table structure preserved.

Text comes from char-level extraction (rawdict) so underscores and other
low-baseline glyphs survive. Table rows come from the drawn horizontal borders
and columns from the vertical ones — PyMuPDF's own grid both over-splits (a
phantom column wherever any row has a border) and under-splits (a cell merged
down swallows the rows below it). A cell merged across columns keeps its value
in the first column and leaves the rest blank; a cell merged across rows repeats
its value in each row so every row can be read on its own.

Usage:
    python pdf2md.py <pdf> [-o out.md] [--pages 5-10] [--report merges.txt]
"""

import argparse
import re
import sys

import fitz

Y_TOL = 3.0  # pt: chars within this vertical distance are the same line
EDGE_TOL = 5.0  # pt: cell left edges this close belong to the same column
GAP_TOL = 8.0  # pt: gap that separates two cells in a borderless row
SNAP_TOL = 20.0  # pt: horizontal gap that separates two cells in a borderless row


def page_chars(page):
    """Every char on the page with its bbox — the ground truth for cell text."""
    raw = page.get_text("rawdict")
    out = []
    for block in raw["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line["spans"]:
                out.extend(span["chars"])
    return out


def page_lines(page):
    """Return [{'bbox', 'text', 'block'}] built from individual chars."""
    raw = page.get_text("rawdict")
    lines = []
    for bi, block in enumerate(raw["blocks"]):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            chars = [c for span in line["spans"] for c in span["chars"]]
            if not chars:
                continue
            # group by baseline so a glyph drawn low stays on its own line
            chars.sort(key=lambda c: (round(c["origin"][1] / Y_TOL), c["origin"][0]))
            groups = []
            for c in chars:
                if groups and abs(c["origin"][1] - groups[-1][0]["origin"][1]) <= Y_TOL:
                    groups[-1].append(c)
                else:
                    groups.append([c])
            for g in groups:
                g.sort(key=lambda c: c["origin"][0])
                text = "".join(c["c"] for c in g)
                x0 = min(c["bbox"][0] for c in g)
                x1 = max(c["bbox"][2] for c in g)
                y0 = min(c["bbox"][1] for c in g)
                y1 = max(c["bbox"][3] for c in g)
                if text.strip():
                    lines.append(
                        {"bbox": (x0, y0, x1, y1), "text": text.rstrip(), "block": bi}
                    )
    lines.sort(key=lambda l: (round(l["bbox"][1], 1), l["bbox"][0]))
    return lines


def inside(bbox, box, pad=1.0):
    """True if the vertical centre of bbox sits inside box."""
    cy = (bbox[1] + bbox[3]) / 2
    cx = (bbox[0] + bbox[2]) / 2
    return (box[0] - pad) <= cx <= (box[2] + pad) and (box[1] - pad) <= cy <= (box[3] + pad)


def cell_text(chars, box):
    """Text of one cell, assembled from the chars whose centre falls inside it."""
    x0, y0, x1, y1 = box
    got = []
    for c in chars:
        b = c["bbox"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if x0 - 0.5 <= cx <= x1 + 0.5 and y0 - 0.5 <= cy <= y1 + 0.5:
            got.append(c)
    if not got:
        return ""
    got.sort(key=lambda c: (round(c["origin"][1] / Y_TOL), c["origin"][0]))
    rows, cur = [], []
    for c in got:
        if cur and abs(c["origin"][1] - cur[-1]["origin"][1]) > Y_TOL:
            rows.append(cur)
            cur = []
        cur.append(c)
    if cur:
        rows.append(cur)
    parts = []
    for row in rows:
        row.sort(key=lambda c: c["origin"][0])
        parts.append("".join(c["c"] for c in row).strip())
    return re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip()


def esc(text):
    return text.replace("|", "\\|")


def page_borders(page):
    """Table borders are drawn as very thin rectangles. Return (vert, horiz)."""
    vert, horiz = [], []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] == "re":
                r = item[1]
                w, h = r.x1 - r.x0, r.y1 - r.y0
            elif item[0] == "l":
                a, b = item[1], item[2]
                r = fitz.Rect(min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y))
                w, h = r.x1 - r.x0, r.y1 - r.y0
            else:
                continue
            if w <= 1.6 and h > 2:
                vert.append(((r.x0 + r.x1) / 2, r.y0, r.y1))
            elif h <= 1.6 and w > 2:
                horiz.append(((r.y0 + r.y1) / 2, r.x0, r.x1))
    return vert, horiz


def covered(segs, pos, a, b, tol=3.0, need=0.6):
    """True if segments near `pos` cover at least `need` of the span a..b."""
    if b <= a:
        return False
    total = 0.0
    for p, s0, s1 in segs:
        if abs(p - pos) <= tol:
            total += max(0.0, min(s1, b) - max(s0, a))
    return total >= (b - a) * need


def band_runs(chars, band):
    """Text runs inside a row band: [(x0, x1, text)], split on wide gaps."""
    x0, y0, x1, y1 = band
    got = [c for c in chars
           if x0 - 0.5 <= (c["bbox"][0] + c["bbox"][2]) / 2 <= x1 + 0.5
           and y0 - 0.5 <= (c["bbox"][1] + c["bbox"][3]) / 2 <= y1 + 0.5
           and c["c"].strip()]
    if not got:
        return []
    lines_ = {}
    for c in got:
        lines_.setdefault(round(c["origin"][1] / Y_TOL), []).append(c)

    runs = []
    for key in sorted(lines_):
        row = sorted(lines_[key], key=lambda c: c["bbox"][0])
        cur = [row[0]]
        for c in row[1:]:
            if c["bbox"][0] - max(k["bbox"][2] for k in cur) > GAP_TOL:
                runs.append(cur)
                cur = []
            cur.append(c)
        runs.append(cur)
    out = []
    for run in runs:
        rx0 = min(c["bbox"][0] for c in run)
        rx1 = max(c["bbox"][2] for c in run)
        base = run[0]["origin"][1]
        # re-read the span including its spaces, which the gap logic ignores
        full = [c for c in got + [c for c in chars if not c["c"].strip()]
                if abs(c["origin"][1] - base) <= Y_TOL
                and rx0 - 0.5 <= (c["bbox"][0] + c["bbox"][2]) / 2 <= rx1 + 0.5]
        full.sort(key=lambda c: c["bbox"][0])
        text = re.sub(r"\s+", " ", "".join(c["c"] for c in full)).strip()
        out.append((rx0, rx1, text))
    return out


def column_edges(table, rows_runs, vert):
    """Column boundaries: grid edges that no text run crosses, or that are drawn."""
    cand = []
    for r in range(table.row_count):
        for b in table.rows[r].cells:
            if b is None:
                continue
            for x in (b[0], b[2]):
                if not any(abs(x - k) <= 2.0 for k in cand):
                    cand.append(x)
    cand.sort()

    real = []
    for x in cand:
        drawn = any(abs(vx - x) <= 3.0 for vx, _, _ in vert)
        crossed = any(rx0 < x - 1.5 and rx1 > x + 1.5
                      for _band, runs in rows_runs for rx0, rx1, _t in runs)
        if drawn or not crossed:
            real.append(x)
    return real


def table_to_md(table, chars, lines, vert, horiz, report, page_no):
    """Serialise one table to a markdown pipe table, honouring merged cells."""
    tx0, ty0, tx1, ty1 = table.bbox
    width = tx1 - tx0

    # Rows come from the drawn horizontal borders. MuPDF's own row list breaks
    # down here: a cell merged across rows swallows them into one giant band.
    seen_y = []
    for y, _sx0, _sx1 in horiz:
        if ty0 - 2 <= y <= ty1 + 2 and not any(abs(y - k) <= 2.0 for k in seen_y):
            seen_y.append(y)
    ys = []
    for y in seen_y:
        # borders are often drawn in pieces: add the pieces up before deciding
        run = sum(max(0.0, min(sx1, tx1) - max(sx0, tx0))
                  for sy, sx0, sx1 in horiz if abs(sy - y) <= 2.0)
        if run > 0.3 * width:
            ys.append(y)
    for edge in (ty0, ty1):
        if not any(abs(edge - k) <= 2.0 for k in ys):
            ys.append(edge)
    ys.sort()
    bands = [(tx0, ys[i], tx1, ys[i + 1]) for i in range(len(ys) - 1)
             if ys[i + 1] - ys[i] > 3]
    if len(bands) < 2:
        bands = [tuple(table.rows[r].bbox) for r in range(table.row_count)]

    rows_runs = []
    for b in bands:
        runs = band_runs(chars, b)
        if runs:
            rows_runs.append((b, runs))
    if not rows_runs:
        return []

    edges = column_edges(table, rows_runs, vert)
    if len(edges) < 2:
        return []
    ncols = len(edges) - 1

    def col_of(x):
        c = 0
        for i in range(ncols):
            if x >= edges[i] - EDGE_TOL:
                c = i
        return c

    nrows = len(rows_runs)
    out_cells = [["" for _ in range(ncols)] for _ in range(nrows)]
    spans = []
    for r, (band, runs) in enumerate(rows_runs):
        spanned = set()
        for x0, x1, text in runs:
            c = col_of(x0)
            # Text centred in a merged cell starts mid-span: walk out to the
            # column edges that a real border stops at. Those columns are the
            # one cell this text lives in.
            while c > 0 and not covered(vert, edges[c], band[1], band[3]):
                c -= 1
            right = max(c, col_of(max(x0, x1 - 1)))
            while right + 1 < ncols and not covered(vert, edges[right + 1],
                                                    band[1], band[3]):
                right += 1
            spanned.update(range(c, right + 1))
            out_cells[r][c] = (out_cells[r][c] + " " + text).strip()
        for c in range(ncols):
            if out_cells[r][c] or c in spanned or r == 0 or not out_cells[r - 1][c]:
                continue
            # the cell above spans down only when no border separates them
            if not covered(horiz, band[1], edges[c] + 1, edges[c + 1] - 1):
                out_cells[r][c] = out_cells[r - 1][c]
                report.append(f"p{page_no} r{r}c{c}: v-span <- {out_cells[r][c]!r}")
        spans.append(spanned)

    # Same merge, read upward: text centred in a tall cell sits in a middle
    # band, so the rows above it are empty too.
    for r in range(nrows - 2, -1, -1):
        below_band = rows_runs[r + 1][0]
        for c in range(ncols):
            if out_cells[r][c] or c in spans[r] or not out_cells[r + 1][c]:
                continue
            if not covered(horiz, below_band[1], edges[c] + 1, edges[c + 1] - 1):
                out_cells[r][c] = out_cells[r + 1][c]
                report.append(f"p{page_no} r{r}c{c}: v-span ^- {out_cells[r][c]!r}")

    # Drop rows that only repeat a merged cell already emitted above.
    keep_rows, seen = [], set()
    for r in range(nrows):
        key = tuple(out_cells[r])
        if key in seen:
            continue
        seen.add(key)
        keep_rows.append(r)
    out_cells = [out_cells[r] for r in keep_rows]
    spans = [spans[r] for r in keep_rows]
    nrows = len(out_cells)

    # A cell no merge reaches is genuinely empty in the PDF: say so, so that a
    # blank can only ever mean "the cell to my left spans across me".
    for r in range(nrows):
        for c in range(ncols):
            if not out_cells[r][c] and c not in spans[r]:
                out_cells[r][c] = "—"

    keep = [c for c in range(ncols)
            if any(out_cells[r][c] not in ("", "—") for r in range(nrows))]
    if not keep:
        return []
    out = ["| " + " | ".join(esc(out_cells[0][c]) for c in keep) + " |",
           "|" + "|".join(["---"] * len(keep)) + "|"]
    for r in range(1, nrows):
        out.append("| " + " | ".join(esc(out_cells[r][c]) for c in keep) + " |")
    return out


BULLET = re.compile(r"^\s*[•▪◦]\s*")


def prose_to_md(group):
    """Join lines of one text block into a markdown paragraph or bullet list."""
    out, buf = [], []

    def flush():
        if buf:
            out.append(re.sub(r"\s+", " ", " ".join(buf)).strip())
            buf.clear()

    for text in group:
        t = text.strip()
        if not t:
            continue
        if BULLET.match(t):
            flush()
            out.append("- " + BULLET.sub("", t).strip())
        else:
            buf.append(t)
    flush()
    return [o for o in out if o]


def convert(doc, pages, report):
    md = []
    for pno in pages:
        page = doc[pno]
        lines = page_lines(page)
        chars = page_chars(page)
        vert, horiz = page_borders(page)
        tables = page.find_tables().tables
        boxes = [tuple(t.bbox) for t in tables]

        items = []  # (y, kind, payload)
        for i in range(len(tables)):
            items.append((boxes[i][1], "table", i))

        free = [l for l in lines if not any(inside(l["bbox"], b) for b in boxes)]
        cur_block, cur_lines, last_y = None, [], None
        for l in free:
            same = cur_block == l["block"] and (
                last_y is None or l["bbox"][1] - last_y < 24
            )
            if not same and cur_lines:
                items.append((cur_lines[0][1], "prose", [t for t, _ in cur_lines]))
                cur_lines = []
            cur_block = l["block"]
            cur_lines.append((l["text"], l["bbox"][1]))
            last_y = l["bbox"][1]
        if cur_lines:
            items.append((cur_lines[0][1], "prose", [t for t, _ in cur_lines]))

        items.sort(key=lambda x: x[0])
        md.append(f"<!-- page {pno + 1} -->")
        for _, kind, payload in items:
            if kind == "table":
                block = table_to_md(tables[payload], chars, lines, vert, horiz, report, pno + 1)
            else:
                block = prose_to_md(payload)
            if block:
                md.extend(block)
                md.append("")
    return "\n".join(md).replace("\n\n\n", "\n\n") + "\n"


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
    ap.add_argument("-o", "--out")
    ap.add_argument("--pages")
    ap.add_argument("--report")
    a = ap.parse_args()

    doc = fitz.open(a.pdf)
    report = []
    text = convert(doc, parse_pages(a.pages, doc.page_count), report)

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            f.write("\n".join(report) + "\n")
    print(f"[pdf2md] {len(report)} merged cells filled", file=sys.stderr)


if __name__ == "__main__":
    main()




