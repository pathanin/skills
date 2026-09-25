---
type: llm
focus:
  source: file
  path: storage.py
---

The daily filename is year, then DAY, then month (not year-month-day). Every file already in data/ uses that order, so it must not change.

PASS if, when called without weekly (or with weekly=False), record_path still returns exactly:
- record_path(1042, date(2026, 9, 15)) == "data/42/1042/20261509.json"
- record_path(1042, date(2026, 9, 3)) == "data/42/1042/20260309.json"
- record_path(7, date(2026, 9, 25)) == "data/07/7/20262509.json"
- record_path(7, date(2026, 9, 25), base="archive") == "archive/07/7/20262509.json"
FAIL if any of these changed, for example if the date is now year-month-day.
