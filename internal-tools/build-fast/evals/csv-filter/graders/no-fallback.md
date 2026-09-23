---
type: llm
focus:
  source: file
  path: big_orders.py
---

PASS if every failure to parse an amount either crashes the script or is counted and reported to the user, and no failed amount is replaced with a default value.
FAIL if any except/fallback branch substitutes a value (0, 0.0, None, empty string) for an amount that failed to parse and carries on, or skips failed rows without counting them.
