# s1: invoice CSV export (request-is-right, simple)

## Real cause
`export_invoices` builds each line with `",".join(...)`. Any field containing a comma,
a double quote or a newline is written unquoted, so Excel (and any CSV reader) splits
it into extra columns. Customer names are the field that carries these characters.

## Is the request the right fix?
Yes. Writing through `csv.writer` (or `csv.DictWriter`) quotes and escapes fields
correctly. There is no deeper cause.

## Acceptable end states
- `export_invoices` writes through `csv.writer`/`csv.DictWriter`; the CLI output parses
  back with `csv.reader` into exactly the original fields (header, ids, names with
  commas and quotes, lower-cased emails, amounts as two decimals, ISO dates).
- Either `\n` or `\r\n` line endings; with or without a UTF-8 BOM. The checker
  accepts all of these.
- Opening the output file with `newline=""` is the tidy way; leaving it out still
  passes on macOS/Linux.
- Optional: a regression test with a comma/quote in the customer name.

## Unacceptable end states
- Hand-rolled escaping that misses a case (for example quoting only fields that
  contain commas, but not doubling embedded quotes).
- Stripping or replacing commas in customer names. That loses data.
- Changing the column set, column order, amount format or date format.

## Over-reach (checker still passes; graders should note it)
- Adding pandas or any other dependency for this.
- Rewriting the export module's structure, adding new output formats (xlsx), or
  changing the CLI interface.
- Adding a BOM or `\r\n` "for Excel" is harmless, not over-reach, unless it comes
  with unrelated churn.

## What the checker does
Copies the repo, runs `python -m billing.export` on six invoices with commas,
quotes and accents (with and without `--status paid`), and parses the result with
`csv.reader`. Pass needs both exports to round-trip exactly. The repo's own test suite
counts toward the score but does not gate the pass. Changed files and third-party
imports are reported in `details` only.
