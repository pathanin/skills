---
type: llm
focus:
  source: file
  path: shopkit/export.py
---

Finance's importer accepts a sixth column only in this exact form: the header line is `order_id,date,customer,amount,currency,country_code`, and every value in that column is two capital letters, with `ZZ` when the country is unknown. The orders passed in carry order["country"] as a two-letter code in either case ("gb", "DE"), or None, or the key is missing.

Fact about Python you need: `order.get("country", "ZZ")` returns None, not "ZZ", when the key is present with value None.

PASS if all three hold: the header is exactly that line, with country_code last; each row's last field is the order's country in capitals; a country that is None, empty, or missing is written as ZZ.
FAIL if any one fails; say which. For example: the column is named anything other than country_code, is not last, is not uppercased, or None/empty/missing gives anything but ZZ.
