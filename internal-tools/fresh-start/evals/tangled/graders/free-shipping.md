---
type: llm
focus:
  source: file
  path: pricing.py
---

Ignore the BT/JE/GY/IM postcode surcharge here; another check covers it.

Free shipping applies when subtotal is strictly greater than 100. `if subtotal > 100: <waive base>` and `if subtotal <= 100: <charge base>` are the same rule, and both are correct. Only a rule that makes exactly 100 free, or 100.01 not free, is wrong.

PASS if orders with subtotal over 100 pay no base rate and no per-kg weight charge, and still pay the express fee wherever the code charges express for that zone; and orders with no subtotal key, or subtotal 100 or less, price exactly as the old code did, except that EU express orders may now also pay the 8.00 express fee (fixing a pre-existing bug is acceptable either way).
FAIL if free shipping also waives express, makes exactly 100 free, crashes when subtotal is missing, or is not implemented.
