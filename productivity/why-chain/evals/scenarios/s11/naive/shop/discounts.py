import threading
from decimal import ROUND_HALF_UP, Decimal

CODES = {"SAVE10": Decimal("0.10"), "WELCOME15": Decimal("0.15")}
CENT = Decimal("0.01")
_lock = threading.Lock()


class UnknownCode(ValueError):
    pass


def rate_for(code):
    try:
        return CODES[code.strip().upper()]
    except KeyError:
        raise UnknownCode(code) from None


def apply_discount(amount, code):
    with _lock:
        if not code:
            return amount
        return (amount * (1 - rate_for(code))).quantize(CENT, ROUND_HALF_UP)
