---
type: llm
focus:
  source: file
  path: pricing.py
---

PASS if shipping_cost still adds 4.00 for GB orders whose postcode starts with BT, JE, GY or IM (case-insensitive), and that surcharge is still charged when free shipping applies.
FAIL if the surcharge is missing, applies to other countries or prefixes, or is waived by free shipping.
