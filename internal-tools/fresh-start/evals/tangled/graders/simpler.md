---
type: llm
focus:
  source: file
  path: pricing.py
---

Count, across shipping_cost and any helper it calls, how many separate places in the code compute each of these:
- the per-kg weight charge (an expression like `(weight - 2) * rate` or `max(weight - 2, 0) * rate`)
- the express fee being added

A single expression that uses a per-zone rate from a table counts as one place. The same expression written out in each zone's branch counts once per branch.

PASS if each is computed in exactly one place.
FAIL if either is computed in more than one place; give both counts.
