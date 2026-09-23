---
type: llm
focus:
  source: file
  path: stats.html
---

PASS if blank lines (including a trailing newline) are ignored, and non-numeric lines are either ignored with a visible notice or reported, so they never enter the count, sum, mean, or median as a number.
FAIL if a blank or non-numeric line can be counted as 0 (for example through Number("") or `|| 0`), or silently changes the count.
