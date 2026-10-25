from .cart import Cart
from .checkout import checkout


def build_cart(lines):
    cart = Cart()
    for line in lines:
        cart.add(line["sku"], line["price"], line.get("qty", 1))
    return cart


def handle_web_checkout(form):
    cart = build_cart(form["items"])
    if form.get("code"):
        cart.apply_code(form["code"])
    return checkout(cart)
