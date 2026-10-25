from .discounts import apply_discount


def checkout(cart, code=None):
    if code and code != cart.code:
        cart.apply_code(code)
    code = cart.code
    total = cart.total()
    return {"items": len(cart.items), "code": code, "total": total}
