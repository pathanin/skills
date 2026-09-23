---
type: llm
focus:
  source: file
  path: pricing.py
---

PASS if shipping_cost has no control-flow state variables (like the original's `done` flag or `cost = None` placeholder that later branches check), no dead branches, and each pricing rule (zone rate, weight charge, surcharge, express, free shipping) is written once. A boolean computed once directly from the input, like `is_eu = country in EU_COUNTRIES`, is fine.
FAIL if a `done`-style flag or placeholder survives, a branch can never run, or the same rule is written out in more than one branch.
