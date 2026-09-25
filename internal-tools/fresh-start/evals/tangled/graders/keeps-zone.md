---
type: llm
focus:
  source: file
  path: pricing.py
---

invoice.py calls shipping_cost(order) and then reads order["shipping_zone"], so that write is part of shipping_cost's contract.

PASS if every call to shipping_cost sets order["shipping_zone"] to "GB" for country GB, "EU" for DE, FR, NL, BE, IT and ES, and "ROW" for every other country, including on orders with subtotal over 100.
FAIL if the write is gone, uses a different key or different values, or is skipped on any path.
