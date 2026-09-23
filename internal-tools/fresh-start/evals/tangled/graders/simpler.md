---
type: llm
focus:
  source: file
  path: pricing.py
---

PASS if shipping_cost has no state flags that are set in one branch and checked in a later one (like `done` or `is_eu` in the original) and no dead branches, so each rule (zone rate, weight charge, surcharge, express, free shipping) appears once.
FAIL if flag variables like `done` survive, or the same rule is written out in more than one branch.
