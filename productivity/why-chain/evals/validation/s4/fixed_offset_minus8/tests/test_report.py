from datetime import date, datetime, timezone
from decimal import Decimal

from sales.orders import Order, parse_order
from sales.receipts import format_receipt
from sales.report import daily_totals


def order(oid, ts, amount, status="paid"):
    return Order(oid, datetime.fromisoformat(ts), Decimal(amount), status)


def test_parse_order():
    o = parse_order({"order_id": "X1", "created_at": "2026-10-05T16:02:11Z", "amount": "6.75", "status": " Paid "})
    assert o.created_at == datetime(2026, 10, 5, 16, 2, 11, tzinfo=timezone.utc)
    assert o.amount == Decimal("6.75")
    assert o.status == "paid"


def test_daily_totals_sums_paid_orders_per_day():
    orders = [
        order("1", "2026-10-05T16:00:00Z", "6.75"),
        order("2", "2026-10-05T18:00:00Z", "12.40"),
        order("3", "2026-10-05T19:00:00Z", "4.50", status="refunded"),
        order("4", "2026-10-06T17:00:00Z", "9.25"),
    ]
    assert daily_totals(orders) == {
        date(2026, 10, 5): (2, Decimal("19.15")),
        date(2026, 10, 6): (1, Decimal("9.25")),
    }


def test_receipt_shows_store_time():
    text = format_receipt(order("9", "2026-10-05T16:02:00Z", "6.75"))
    assert "Oct 05, 2026 09:02 AM" in text
    assert "Total: 6.75 USD" in text
