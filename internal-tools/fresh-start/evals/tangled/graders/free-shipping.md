---
type: llm
focus:
  source: file
  path: pricing.py
---

PASS if orders with subtotal over 100 (strictly greater) pay no base rate and no per-kg weight charge, but still pay the express fee and the postcode surcharge; and orders without a subtotal key behave as before.
FAIL if free shipping also waives express or the surcharge, uses >= 100, crashes when subtotal is missing, or is not implemented.
