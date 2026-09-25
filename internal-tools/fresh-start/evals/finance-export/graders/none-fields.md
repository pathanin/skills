---
type: llm
focus:
  source: file
  path: shopkit/export.py
---

The loader that feeds export_orders produces orders where the keys are present but the values can be None: "customer" is None for guest checkouts, "currency" is None for old orders, and "email" is None for phone orders.

Fact about Python you need: `order.get("currency", "GBP")` returns None, not "GBP", when the key exists with value None. The same goes for `.get("customer", "")` and `.get("email", "")`. Forms like `order.get("currency") or "GBP"` do handle None.

PASS if all three hold for orders where the key is present with value None: customer None is written as an empty field (not the text "None", no crash); currency None or "" is written as GBP; email None does not crash and the order is exported.
FAIL if any one fails; say which.
