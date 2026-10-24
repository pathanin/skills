from zoneinfo import ZoneInfo

from sales.config import CURRENCY, STORE_NAME, STORE_TZ
from sales.orders import Order


def format_receipt(order: Order) -> str:
    local = order.created_at.astimezone(ZoneInfo(STORE_TZ))
    return "\n".join([
        STORE_NAME,
        f"Order {order.order_id}",
        local.strftime("%b %d, %Y %I:%M %p"),
        f"Total: {order.amount:.2f} {CURRENCY}",
    ])
