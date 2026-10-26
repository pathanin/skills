from dataclasses import dataclass


@dataclass(frozen=True)
class Receipt:
    event_id: str
    event_type: str
    result: dict


def receipt_for(event, result):
    return Receipt(event_id=event.id, event_type=event.type, result=result)


class ReceiptLog:
    """Receipts served by the customer-facing receipts endpoint."""

    def __init__(self):
        self._items = []

    def add(self, receipt):
        self._items.append(receipt)
        return receipt

    def get(self, event_id):
        for receipt in reversed(self._items):
            if receipt.event_id == event_id:
                return receipt
        return None

    def all(self):
        return list(self._items)
