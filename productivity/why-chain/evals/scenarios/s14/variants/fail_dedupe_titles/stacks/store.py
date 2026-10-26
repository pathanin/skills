"""In-memory branch catalogue used by the search endpoint and tests."""

from .models import Book
from .search import search


# A small slice of the branch catalogue. Popular titles are held in several
# copies, each with its own accession id.
DEMO_BOOKS = [
    Book("b-001", "Dune", "Frank Herbert", 1965),
    Book("b-002", "Dune", "Frank Herbert", 1965),
    Book("b-003", "Dune", "Frank Herbert", 1965),
    Book("b-004", "Emma", "Jane Austen", 1815),
    Book("b-005", "Middlemarch", "George Eliot", 1871),
    Book("b-006", "Middlemarch", "George Eliot", 1871),
    Book("b-007", "Persuasion", "Jane Austen", 1817),
    Book("b-008", "The Dispossessed", "Ursula K. Le Guin", 1974),
    Book("b-009", "The Hobbit", "J.R.R. Tolkien", 1937),
    Book("b-010", "The Hobbit", "J.R.R. Tolkien", 1937),
    Book("b-011", "The Left Hand of Darkness", "Ursula K. Le Guin", 1969),
    Book("b-012", "Wuthering Heights", "Emily Bronte", 1847),
]


class Catalog:
    def __init__(self, books):
        self._books = list(books)

    def add(self, book):
        self._books.append(book)

    def all(self):
        return list(self._books)

    def search(self, query="", limit=10, after=None):
        return search(self._books, query=query, limit=limit, after=after)
