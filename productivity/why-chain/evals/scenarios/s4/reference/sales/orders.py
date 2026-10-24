import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class Order:
    order_id: str
    created_at: datetime
    amount: Decimal
    status: str
    register: str = "web"


def parse_order(row: dict) -> Order:
    return Order(
        order_id=row["order_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        amount=Decimal(row["amount"]),
        status=row["status"].strip().lower(),
        register=row.get("register") or "web",
    )


def load_orders(path: Path) -> list[Order]:
    with open(path, newline="", encoding="utf-8") as fh:
        return [parse_order(row) for row in csv.DictReader(fh)]
