from dataclasses import dataclass


@dataclass(frozen=True)
class Invoice:
    id: int
    customer: str
    month: str  # "YYYY-MM"
    amount_cents: int
