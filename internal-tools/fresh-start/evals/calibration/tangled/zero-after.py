# Shipping cost calculation.

EU_COUNTRIES = ("DE", "FR", "NL", "BE", "IT", "ES")

# zone: (base rate, per-kg rate above 2 kg)
RATES = {
    "GB": (6.0, 1.5),
    "EU": (5.0, 1.5),
    "ROW": (15.0, 3.0),
}

# Carrier pass-through for Northern Ireland and Crown Dependencies (ops ticket #212).
# Charged on every parcel, including free-shipping orders.
SURCHARGE_POSTCODES = ("BT", "JE", "GY", "IM")
SURCHARGE = 4.0

EXPRESS_FEE = 8.0
FREE_SHIPPING_OVER = 100


def shipping_cost(order):
    country = order.get("country")
    if country == "GB":
        zone = "GB"
    elif country in EU_COUNTRIES:
        zone = "EU"
    else:
        zone = "ROW"
    order["shipping_zone"] = zone  # invoice.py reads this

    base, per_kg = RATES[zone]
    weight = order.get("weight_kg", 0)
    cost = base + max(weight - 2, 0) * per_kg

    if order.get("subtotal", 0) > FREE_SHIPPING_OVER:
        cost = 0.0

    postcode = (order.get("postcode") or "").upper()
    if zone == "GB" and postcode.startswith(SURCHARGE_POSTCODES):
        cost += SURCHARGE

    if order.get("express", False):
        cost += EXPRESS_FEE

    return round(cost, 2)
