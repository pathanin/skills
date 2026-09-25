import os

HEADER = "order_id,date,customer,amount,currency\n"
DEFAULT_CURRENCY = "GBP"
TEST_EMAIL_SUFFIX = "@example.com"


def _is_test_order(order):
    email = order.get("email") or ""
    return email.lower().endswith(TEST_EMAIL_SUFFIX)


def _format_row(order):
    amount = order["total"]
    if order.get("status") == "refunded":
        amount = 0 - amount  # avoid "-0.00" for zero-value refunds
    customer = (order.get("customer") or "").replace(",", " ")
    currency = order.get("currency") or DEFAULT_CURRENCY
    return "%s,%s,%s,%.2f,%s" % (
        order["id"],
        order["created"].strftime("%d/%m/%Y"),
        customer,
        amount,
        currency,
    )


def export_orders(orders, path):
    rows = [
        _format_row(o)
        for o in orders
        if o.get("status") != "cancelled" and not _is_test_order(o)
    ]

    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        f.write(HEADER)
        for row in rows:
            f.write(row + "\n")
    os.replace(tmp_path, path)

    return len(rows)
