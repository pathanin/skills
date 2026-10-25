from decimal import Decimal

import pytest

from shop.discounts import UnknownCode, apply_discount


def test_percent():
    assert apply_discount(Decimal("50.00"), "save10") == Decimal("45.00")


def test_unknown():
    with pytest.raises(UnknownCode):
        apply_discount(Decimal("1.00"), "NOPE")
