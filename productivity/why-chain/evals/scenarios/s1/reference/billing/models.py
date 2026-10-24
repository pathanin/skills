from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Invoice:
    id: str
    customer: str
    email: str
    amount: Decimal
    issued_on: date
    status: str = "open"

    @classmethod
    def from_dict(cls, raw: dict) -> "Invoice":
        return cls(
            id=raw["id"],
            customer=raw["customer"].strip(),
            email=raw["email"].strip().lower(),
            amount=Decimal(str(raw["amount"])),
            issued_on=date.fromisoformat(raw["issued_on"]),
            status=raw.get("status", "open"),
        )
