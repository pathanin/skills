# Shipping cost calculation.


def shipping_cost(order):
    country = order.get("country")
    weight = order.get("weight_kg", 0)
    express = order.get("express", False)
    postcode = (order.get("postcode") or "").upper()
    subtotal = order.get("subtotal", 0)

    if country == "GB":
        zone = "GB"
    elif country in ("DE", "FR", "NL", "BE", "IT", "ES"):
        zone = "EU"
    else:
        zone = "ROW"
    order["shipping_zone"] = zone

    if subtotal > 100:
        return round(8.0 if express else 0.0, 2)

    if zone == "GB":
        cost = 6.0 + max(0, weight - 2) * 1.5
        if postcode.startswith(("BT", "JE", "GY", "IM")):
            cost += 4.0
    elif zone == "EU":
        cost = 5.0 + max(0, weight - 2) * 1.5
    else:
        cost = 15.0 + max(0, weight - 2) * 3.0

    if express:
        cost += 8.0

    return round(cost, 2)
