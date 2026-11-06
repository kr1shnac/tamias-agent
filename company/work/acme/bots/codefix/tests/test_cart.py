import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cart import total  # noqa: E402


def test_total_multiplies_quantity_by_price():
    assert total([{"price": 2.5, "qty": 4}]) == 10.0


def test_empty_cart_is_zero():
    assert total([]) == 0
