import csv
import os
import tempfile

HEADER = ["order_id", "date", "customer", "amount", "currency", "country_code"]


def export_orders(orders, path):
    rows = []
    for order in orders:
        email = (order.get("email") or "").lower()
        if order.get("status") == "cancelled" or email.endswith("@example.com"):
            continue
        amount = order["total"]
        if order.get("status") == "refunded":
            amount = -amount
        rows.append([
            order["id"],
            order["created"].strftime("%d/%m/%Y"),
            (order.get("customer") or "").replace(",", " "),
            "%.2f" % amount,
            order.get("currency") or "GBP",
            (order.get("country") or "ZZ").upper(),
        ])
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    with os.fdopen(fd, "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)
    os.replace(tmp, path)
    return len(rows)
