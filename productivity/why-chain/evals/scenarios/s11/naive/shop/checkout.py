from .discounts import apply_discount


def checkout(cart, code=None):
    code = code or cart.code
    total = apply_discount(cart.total(), code)
    return {"items": len(cart.items), "code": code, "total": total}
