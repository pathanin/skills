---
name: pdf-to-md
description: Convert a PDF (or a page range / one section of it) to markdown that keeps the tables, then verify no text was lost. Use whenever the user asks to turn a PDF into markdown, extract a section of a PDF, or rewrite a PDF table as markdown — including announcement, spec, and report PDFs with merged-cell Word tables.
---

# PDF to markdown

Never transcribe a PDF by hand. Hand-typed tables are where errors enter. Run the
converter, verify with the checker, then edit only structure — never re-type values.

## Requirements

PyMuPDF (`import fitz`). Install with `pip install pymupdf` if missing.
The built-in Read tool cannot render PDFs without poppler; do not rely on it.

## Workflow

1. **Convert.** Whole file, or a page range:
   ```
   python <skill>/scripts/pdf2md.py IN.pdf -o out.md [--pages 5-10] [--report merges.txt]
   ```
   `out.md` carries `<!-- page N -->` markers. `--report` lists every merged cell
   the script filled and every stray line it recovered — read it when a table
   looks odd.

2. **Verify.** Token coverage against the source:
   ```
   python <skill>/scripts/compare.py IN.pdf out.md [--pages 5-10]
   ```
   - `missing tokens: 0` is the bar. Anything missing is a real defect — fix the
     markdown (or the script) before shipping.
   - Extra tokens are expected: a cell merged across rows is repeated so each row
     stands alone. Scan the list; extras that are not merge repeats mean text got
     duplicated into two cells.

3. **Shape it.** Structure only — never retype a value. Most of it is mechanical:
   ```
   python <skill>/scripts/shape.py out.md section.md \
       --start "^2\. TFEX" --stop "^3\. Equity" \
       --heading "^Project plan$=>## Project plan"
   ```
   It drops page markers and page numbers, rejoins a table split across pages,
   merges a two-level header into one row (`Session state — Current`), and
   applies the heading rules you pass. Anything left — a header the converter
   could not split, a stray artefact — edit by hand afterwards.

   Caveat: it deletes any line that is only digits, so a table cell or list item
   standing alone on its own line as a bare number would go too. The coverage
   check in step 4 catches that.

4. **Re-verify.** Run `compare.py` again on the finished file, with the page
   range the section covers. Expect exactly two kinds of leftover:
   page numbers, and text from a neighbouring section on a shared page. Anything
   else missing is a defect. State what you dropped when you report.

## Conventions the script uses

- **Blank cell** = the cell to its left spans across it (markdown has no colspan).
- **`—`** = a cell of its own that is empty in the PDF. Blank and `—` mean
  different things: `| 17:45 |  |` says the 17:45 cell covers both columns,
  `| 17:45 | — |` says the second column has no value.
- **Repeated value down a column** = one cell in the PDF merged over those rows.
- Cell text is read char by char, so `SERIES_GEN_NIGHT_D` keeps its underscores.
  Plain `page.get_text()` drops them onto a second line — never use it for tables.

## Known limits

- A two-level header (`Test environment` over `SET CONNECT` / `SET CLEAR`) comes
  out as two rows. Merge them by hand in step 3.
- A cell whose text is centred across a merge lands in the first column of the
  merge. That matches the PDF, but check it when a value looks off by a column.
- A cell merged **across a page break** loses its value on the later page: that
  page prints nothing, so those rows come out `—`. After `shape.py` rejoins the
  table, check its last rows against the PDF and restate the value by hand.
- Scanned PDFs have no text layer: the script yields nothing and OCR is needed.
- Images and charts are ignored — describe them separately if they matter.
