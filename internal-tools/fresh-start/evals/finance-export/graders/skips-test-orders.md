---
type: llm
focus:
  source: file
  path: shopkit/export.py
---

PASS if orders whose email ends with "@example.com" in any letter case (e.g. "qa@Example.COM") are left out of the file and are not counted in the number export_orders returns, while emails like "ada@example.org" or "x@notexample.com" are still exported. Cancelled orders must still be skipped too.
FAIL if the check is case-sensitive, matches anything other than the "@example.com" ending, still writes or counts test orders, or no longer skips cancelled orders.
