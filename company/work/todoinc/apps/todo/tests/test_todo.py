import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.todo import add, complete  # noqa: E402


def test_add_appends_an_open_item():
    items = add([], "buy milk")
    assert items[0]["done"] is False


def test_complete_marks_the_matching_item():
    items = complete(add([], "buy milk"), "buy milk")
    assert items[0]["done"] is True
