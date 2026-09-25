---
type: llm
focus:
  source: file
  path: pricing.py
---

Ignore the BT/JE/GY/IM postcode surcharge here; another check covers it.

The rates shipping_cost must charge:
- zone rate: GB 6.00; EU (DE, FR, NL, BE, IT, ES) 5.00; any other country 15.00
- weight charge for each kg over 2 kg: 1.50 per kg for GB and EU, 3.00 per kg for other countries
- express: 8.00. For EU, charging 0.00 or 8.00 is acceptable (the old code had a bug there).

Free shipping: when order["subtotal"] is strictly greater than 100, the zone rate and the weight charge are waived, and express is still charged. `if subtotal > 100: <waive>` and `if subtotal <= 100: <charge>` are the same rule.

PASS if all of these hold:
1. subtotal over 100 waives both the zone rate and the weight charge
2. subtotal of exactly 100 is not free
3. express is still added on free orders, in every zone where the code charges express
4. an order with no "subtotal" key is not free and does not crash
5. orders that aren't free pay the zone rate and weight charge listed above
FAIL if any item fails; say which.
