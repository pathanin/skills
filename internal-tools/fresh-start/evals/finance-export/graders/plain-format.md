---
type: llm
focus:
  source: file
  path: shopkit/export.py
---

Finance's importer splits the file on "\n" and each line on ",", and rejects any "\r" or double quote. So the exported file must use plain "\n" line endings, never quote a field, and turn commas in customer names into spaces.

Facts about Python you need: `csv.writer` defaults to `lineterminator="\r\n"` and `quoting=csv.QUOTE_MINIMAL`, which wraps any field containing a comma in double quotes. Opening the file with `newline=""` does not change the writer's line terminator. A csv.writer is only acceptable if it passes `lineterminator="\n"` and the customer's commas are replaced before writing (or quoting is disabled).

PASS if all three hold: every line written ends with "\n" and never "\r\n"; no field is ever wrapped in quotes; a comma in the customer name is replaced with a space.
FAIL if any one fails; say which.
