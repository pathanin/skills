# Shipping cost calculation.

EU_COUNTRIES = ("DE", "FR", "NL", "BE", "IT", "ES")
# Carrier pass-through for Northern Ireland and Crown Dependencies (ops ticket #212).
# Charged on every parcel, including free-shipping orders.
SURCHARGE_POSTCODES = ("BT", "JE", "GY", "IM")
SURCHARGE = 4.0
EXPRESS_FEE = 8.0
FREE_SHIPPING_OVER = 100

# zone: (base rate, per kg over 2 kg)
RATES = {"GB": (6.0, 1.5), "EU": (5.0, 1.5), "ROW": (15.0, 3.0)}


def shipping_zone(country):
    if country == "GB":
        return "GB"
    if country in EU_COUNTRIES:
        return "EU"
    return "ROW"


def shipping_cost(order):
    zone = shipping_zone(order.get("country"))
    order["shipping_zone"] = zone  # read by invoice.invoice_lines

    weight = order.get("weight_kg", 0)
    postcode = (order.get("postcode") or "").upper()

    cost = 0.0
    if order.get("subtotal", 0) <= FREE_SHIPPING_OVER:
        base, per_kg = RATES[zone]
        cost += base + max(weight - 2, 0) * per_kg
    if zone == "GB" and postcode.startswith(SURCHARGE_POSTCODES):
        cost += SURCHARGE
    if order.get("express", False):
        cost += EXPRESS_FEE
    return round(cost, 2)
