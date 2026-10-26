from stacks.models import Book
from stacks.search import search


UNIQUE = [
    Book("u-1", "A Room with a View", "E. M. Forster", 1908),
    Book("u-2", "Beloved", "Toni Morrison", 1987),
    Book("u-3", "Kindred", "Octavia Butler", 1979),
    Book("u-4", "Possession", "A. S. Byatt", 1990),
    Book("u-5", "The Remains of the Day", "Kazuo Ishiguro", 1989),
]


def test_empty_query_returns_everything():
    page = search(UNIQUE)
    assert [book.id for book in page["items"]] == [book.id for book in UNIQUE]


def test_matches_title_case_insensitively():
    page = search(UNIQUE, query="BELOVED")
    assert [book.id for book in page["items"]] == ["u-2"]


def test_matches_author():
    page = search(UNIQUE, query="butler")
    assert [book.id for book in page["items"]] == ["u-3"]


def test_results_are_in_title_order():
    page = search(UNIQUE)
    titles = [book.title.casefold() for book in page["items"]]
    assert titles == sorted(titles)


def test_limit_is_respected():
    page = search(UNIQUE, limit=2)
    assert len(page["items"]) == 2
    assert page["next_cursor"] is not None


def test_last_page_has_no_cursor():
    page = search(UNIQUE, limit=len(UNIQUE))
    assert page["next_cursor"] is None
