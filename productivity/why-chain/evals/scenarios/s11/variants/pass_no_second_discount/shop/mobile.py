from .checkout import checkout
from .web import build_cart


def handle_app_checkout(payload):
    cart = build_cart(payload["items"])
    return checkout(cart, code=payload.get("code"))
