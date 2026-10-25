from decimal import Decimal

from shop.web import build_cart, handle_web_checkout

ITEMS = [{"sku": "mug", "price": "12.50", "qty": 2}, {"sku": "tee", "price": "25.00"}]


def test_web_code_applied_once():
    assert handle_web_checkout({"items": ITEMS, "code": "SAVE10"})["total"] == Decimal("45.00")


def test_cart_preview_matches_receipt():
    from shop.checkout import checkout
    cart = build_cart(ITEMS)
    cart.apply_code("SAVE10")
    assert cart.total() == checkout(cart)["total"] == Decimal("45.00")
