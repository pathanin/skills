from decimal import Decimal

from .discounts import apply_discount, rate_for


class Cart:
    def __init__(self):
        self.items = []
        self.code = None

    def add(self, sku, price, qty=1):
        self.items.append((sku, Decimal(str(price)), int(qty)))

    def apply_code(self, code):
        rate_for(code)  # validate
        self.code = code

    def subtotal(self):
        return sum((price * qty for _, price, qty in self.items), Decimal("0.00"))

    def total(self):
        """What the cart page shows."""
        return self.subtotal()
