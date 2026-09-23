---
type: llm
focus:
  source: file
  path: pricing.py
---

PASS if orders with subtotal over 100 (strictly greater) pay no base rate and no per-kg weight charge but still pay the postcode surcharge, and pay the express fee wherever the code charges express for that zone; and orders without a subtotal key price exactly as the old code did, except that EU express orders may now also pay the 8.00 express fee (fixing a pre-existing bug is acceptable either way).
FAIL if free shipping also waives express or the surcharge, uses >= 100, crashes when subtotal is missing, or is not implemented.
