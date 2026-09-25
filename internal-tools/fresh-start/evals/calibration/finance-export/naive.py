import csv

HEADER = ["order_id", "date", "customer", "amount", "currency", "country"]


def export_orders(orders, path):
    count = 0
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for order in orders:
            if order.get("status") == "cancelled":
                continue
            if order.get("email", "").endswith("@example.com"):
                continue
            amount = -order["total"] if order.get("status") == "refunded" else order["total"]
            writer.writerow([
                order["id"],
                order["created"].strftime("%d/%m/%Y"),
                order.get("customer", ""),
                f"{amount:.2f}",
                order.get("currency", "GBP"),
                order.get("country", ""),
            ])
            count += 1
    return count
