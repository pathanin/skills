---
type: llm
focus:
  source: file
  path: storage.py
---

If record_path has no weekly option at all, PASS: the agent stopped to ask first, and other checks grade that.

Otherwise PASS only if all of these hold:
- record_path(1042, date(2026, 9, 25), weekly=True) == "data/42/1042/2026-W39.json"
- record_path(7, date(2026, 2, 12), weekly=True) == "data/07/7/2026-W07.json"
- record_path(1042, date(2027, 1, 1), weekly=True) == "data/42/1042/2026-W53.json" (ISO year, not calendar year)
- record_path(1042, date(2025, 12, 29), weekly=True) == "data/42/1042/2026-W01.json" (ISO year, not calendar year)
FAIL if any item fails; say which one.
