# Shipping cost calculation.


def shipping_cost(order):
    country = order.get("country")
    weight = order.get("weight_kg", 0)
    express = order.get("express", False)
    postcode = order.get("postcode", "") or ""
    cost = None
    done = False
    is_eu = False
    if country in ("DE", "FR", "NL", "BE", "IT", "ES"):
        is_eu = True
    if country == "GB":
        order["shipping_zone"] = "GB"
        base = 6.0
        if weight > 2:
            base = base + (weight - 2) * 1.5
        if postcode.upper().startswith(("BT", "JE", "GY", "IM")):
            base = base + 4.0
        if express:
            base = base + 8.0
        cost = base
        done = True
    if not done:
        if is_eu:
            order["shipping_zone"] = "EU"
            base = 5.0
            if weight > 2:
                base = base + (weight - 2) * 1.5
            cost = base
            done = True
            # express handled below
    if not done:
        order["shipping_zone"] = "ROW"
        base = 15.0
        if weight > 2:
            base = base + (weight - 2) * 3.0
        if express:
            base = base + 8.0
        cost = base
        done = True
    if express and not is_eu and country != "GB" and done == False:
        cost = cost + 8.0
    return round(cost, 2)
