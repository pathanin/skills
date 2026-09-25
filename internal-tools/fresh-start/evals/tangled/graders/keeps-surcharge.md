---
type: llm
focus:
  source: file
  path: pricing.py
---

PASS if shipping_cost adds 4.00 for GB orders whose postcode starts with BT, JE, GY or IM (case-insensitive), both on ordinary orders and on orders with subtotal over 100. If free shipping isn't implemented at all, only the ordinary-order part applies.
FAIL if the surcharge is missing, applies to other countries or prefixes, or is waived on orders with subtotal over 100.
