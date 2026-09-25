---
type: llm
focus:
  source: file
  path: storage.py
---

If record_path has no weekly option at all, PASS: the agent stopped to ask first, and other checks grade that.

Otherwise, judge how the weekly name is built rather than computing calendar dates yourself. PASS only if all of these hold:
- both the year and the week number come from the ISO calendar: `day.isocalendar()`, or `strftime` with `%G` and `%V`. Using `day.year`, `%Y`, `%W` or `%U` for either part is wrong, because they disagree with ISO at year boundaries (e.g. 2027-01-01 is ISO week 53 of 2026).
- the week number is zero-padded to two digits, and the filename is `<ISO year>-W<week>.json`, e.g. `2026-W07.json`.
- the file sits in the same directory as the daily files: `<base>/<user_id % 100, two digits>/<user_id>/`.
FAIL if any item fails; say which one.
