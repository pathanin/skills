from stacks.api import handle_search
from stacks.models import Book
from stacks.store import DEMO_BOOKS, Catalog


def test_demo_catalog_holds_multiple_copies():
    copies = [book for book in DEMO_BOOKS if book.title == "Dune"]
    assert len(copies) == 3


def test_api_returns_plain_dicts():
    catalog = Catalog([Book("b-1", "Emma", "Jane Austen", 1815)])
    result = handle_search(catalog, {"q": "emma"})
    assert result["items"] == [
        {"id": "b-1", "title": "Emma", "author": "Jane Austen", "year": 1815}
    ]
    assert result["next_cursor"] is None


def test_api_honours_limit():
    catalog = Catalog(DEMO_BOOKS)
    result = handle_search(catalog, {"limit": "2"})
    assert len(result["items"]) == 2
    assert result["next_cursor"] is not None


def test_api_bad_limit_falls_back_to_default():
    many = [
        Book("m-%02d" % number, "Title %02d" % number, "An Author", 2000)
        for number in range(12)
    ]
    result = handle_search(Catalog(many), {"limit": "nope"})
    assert len(result["items"]) == 10
