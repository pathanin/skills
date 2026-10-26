"""Regression tests for paging through non-unique titles."""

from stacks.models import Book
from stacks.search import search
from stacks.store import DEMO_BOOKS


def _walk(books, query="", limit=2):
    ids = []
    after = None
    while True:
        page = search(books, query=query, limit=limit, after=after)
        ids.extend(book.id for book in page["items"])
        after = page["next_cursor"]
        if after is None:
            return ids


def test_all_dune_copies_are_returned():
    ids = _walk(DEMO_BOOKS, query="dune", limit=2)
    assert ids == ["b-001", "b-002", "b-003"]


def test_paging_visits_every_copy_exactly_once():
    expected = [book.id for book in DEMO_BOOKS]
    for limit in (1, 2, 3, 5):
        assert sorted(_walk(DEMO_BOOKS, limit=limit)) == sorted(expected)
