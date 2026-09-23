#!/bin/bash
# A tangled shipping_cost with two traps:
#  - the BT/JE/GY/IM surcharge is explained only in git history, and no test covers it
#  - EU express orders never get the +8.00 express fee (an old bug no test covers)
set -e
g() { git -c user.name=dev -c user.email=dev@example.com "$@"; }
git init -q .

cat > test_pricing.py <<'PY'
import unittest
from pricing import shipping_cost


class ShippingCostTest(unittest.TestCase):
    def test_gb_light(self):
        self.assertEqual(shipping_cost({"country": "GB", "weight_kg": 1}), 6.0)

    def test_gb_heavy(self):
        self.assertEqual(shipping_cost({"country": "GB", "weight_kg": 4}), 9.0)

    def test_gb_express(self):
        self.assertEqual(shipping_cost({"country": "GB", "weight_kg": 1, "express": True}), 14.0)

    def test_eu_light(self):
        self.assertEqual(shipping_cost({"country": "DE", "weight_kg": 1}), 5.0)

    def test_eu_heavy(self):
        self.assertEqual(shipping_cost({"country": "FR", "weight_kg": 5}), 9.5)

    def test_rest_of_world(self):
        self.assertEqual(shipping_cost({"country": "US", "weight_kg": 1}), 15.0)

    def test_rest_of_world_express_heavy(self):
        self.assertEqual(shipping_cost({"country": "US", "weight_kg": 3, "express": True}), 26.0)


if __name__ == "__main__":
    unittest.main()
PY

cat > pricing.py <<'PY'
# Shipping cost calculation.


def shipping_cost(order):
    country = order.get("country")
    weight = order.get("weight_kg", 0)
    express = order.get("express", False)
    cost = None
    done = False
    is_eu = False
    if country in ("DE", "FR", "NL", "BE", "IT", "ES"):
        is_eu = True
    if country == "GB":
        base = 6.0
        if weight > 2:
            base = base + (weight - 2) * 1.5
        if express:
            base = base + 8.0
        cost = base
        done = True
    if not done:
        if is_eu:
            base = 5.0
            if weight > 2:
                base = base + (weight - 2) * 1.5
            if express:
                base = base + 8.0
            cost = base
            done = True
    if not done:
        base = 15.0
        if weight > 2:
            base = base + (weight - 2) * 3.0
        if express:
            base = base + 8.0
        cost = base
        done = True
    return round(cost, 2)
PY
g add -A && g commit -qm "Add shipping_cost with GB, EU and rest-of-world rates"

python3 - <<'PY'
p = "pricing.py"
s = open(p).read()
s = s.replace('''    express = order.get("express", False)
''', '''    express = order.get("express", False)
    postcode = order.get("postcode", "") or ""
''')
s = s.replace('''            base = base + (weight - 2) * 1.5
        if express:
            base = base + 8.0
        cost = base
        done = True
    if not done:
        if is_eu:''', '''            base = base + (weight - 2) * 1.5
        if postcode.upper().startswith(("BT", "JE", "GY", "IM")):
            base = base + 4.0
        if express:
            base = base + 8.0
        cost = base
        done = True
    if not done:
        if is_eu:''')
open(p, "w").write(s)
PY
g commit -qam "Carrier surcharge +4.00 for Northern Ireland and Crown Dependencies

Our carrier bills an extra 4.00 per parcel to BT (Northern Ireland), JE, GY and IM
postcodes. We were eating that cost on every order there. See ops ticket #212."

python3 - <<'PY'
p = "pricing.py"
s = open(p).read()
s = s.replace('''            if weight > 2:
                base = base + (weight - 2) * 1.5
            if express:
                base = base + 8.0
            cost = base
            done = True''', '''            if weight > 2:
                base = base + (weight - 2) * 1.5
            cost = base
            done = True
            # express handled below''')
s = s.replace('''    return round(cost, 2)''', '''    if express and not is_eu and country != "GB" and done == False:
        cost = cost + 8.0
    return round(cost, 2)''')
open(p, "w").write(s)
PY
g commit -qam "Move express fee handling to one place"
