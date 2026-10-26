from hookrelay.events import Event
from hookrelay.receipts import Receipt, ReceiptLog, receipt_for


def test_add_and_get():
    log = ReceiptLog()
    receipt = receipt_for(Event("evt_1", "ping", {}), {"pong": True})
    log.add(receipt)
    assert log.get("evt_1") == receipt
    assert log.get("missing") is None


def test_latest_receipt_wins():
    log = ReceiptLog()
    first = Receipt("evt_1", "ping", {"n": 1})
    second = Receipt("evt_1", "ping", {"n": 2})
    log.add(first)
    log.add(second)
    assert log.get("evt_1") == second


def test_all_returns_a_copy():
    log = ReceiptLog()
    log.add(Receipt("evt_1", "ping", {"pong": True}))
    items = log.all()
    items.clear()
    assert len(log.all()) == 1
