import os

HEADER = "order_id,date,customer,amount,currency,country_code"


def _is_test_order(order):
    return (order.get("email") or "").lower().endswith("@example.com")


def _row(order):
    amount = order["total"]
    if order.get("status") == "refunded":
        amount = -amount
    customer = (order.get("customer") or "").replace(",", " ")
    currency = order.get("currency") or "GBP"
    country = (order.get("country") or "ZZ").upper()
    return "%s,%s,%s,%.2f,%s,%s" % (order["id"], order["created"].strftime("%d/%m/%Y"), customer, amount, currency, country)


def export_orders(orders, path):
    rows = [_row(o) for o in orders if o.get("status") != "cancelled" and not _is_test_order(o)]
    # Write then rename: finance's poller must never see a partial file (docs/runbook.md).
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write("".join(line + "\n" for line in [HEADER] + rows))
    os.replace(tmp, path)
    return len(rows)
