---
type: llm
focus:
  source: file
  path: stats.html
---

PASS if the median sorts the numbers numerically (a comparator such as (a, b) => a - b, or a typed array) and, for an even count, averages the two middle values.
FAIL if it uses a bare .sort() on numbers, or picks a single middle value for even counts.
