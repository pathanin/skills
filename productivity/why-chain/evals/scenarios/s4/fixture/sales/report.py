"""Daily sales totals for paid orders."""
import argparse
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from sales.orders import Order, load_orders


def daily_totals(orders: list[Order]) -> dict[date, tuple[int, Decimal]]:
    counts: dict[date, int] = defaultdict(int)
    totals: dict[date, Decimal] = defaultdict(Decimal)
    for order in orders:
        if order.status != "paid":
            continue
        day = order.created_at.date()
        counts[day] += 1
        totals[day] += order.amount
    return {day: (counts[day], totals[day]) for day in sorted(totals)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("orders_csv", type=Path)
    args = parser.parse_args(argv)

    out = sys.stdout
    out.write("date,orders,total\n")
    for day, (count, total) in daily_totals(load_orders(args.orders_csv)).items():
        out.write(f"{day.isoformat()},{count},{total:.2f}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
