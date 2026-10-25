from decimal import Decimal

from shop.mobile import handle_app_checkout

ITEMS = [{"sku": "mug", "price": "12.50", "qty": 2}, {"sku": "tee", "price": "25.00"}]


def test_app_checkout_with_code():
    assert handle_app_checkout({"items": ITEMS, "code": "SAVE10"})["total"] == Decimal("45.00")


def test_app_checkout_without_code():
    assert handle_app_checkout({"items": ITEMS})["total"] == Decimal("50.00")
