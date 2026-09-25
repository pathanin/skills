---
type: llm
focus:
  source: file
  path: shopkit/export.py
---

PASS if export_orders writes the whole file somewhere other than `path` first (for example `path + ".tmp"`, or a temp file in the same directory) and then moves it onto `path` with `os.replace`, `os.rename`, or `Path.replace`/`Path.rename`.
FAIL if it opens `path` itself for writing.
