"""Catalogue search with cursor pagination.

The public contract is a dict with ``items`` (a page of Book objects) and
``next_cursor`` (pass it back as ``after`` to fetch the next page, or None
when there are no more results).
"""

DEFAULT_LIMIT = 10


def _matches(book, query):
    needle = query.strip().casefold()
    if not needle:
        return True
    return needle in book.title.casefold() or needle in book.author.casefold()


def _sort_key(book):
    return book.title.casefold()


def _dedupe_titles(books):
    """Keep one record per title so paging cannot stall on a shared title."""
    seen = set()
    unique = []
    for book in books:
        title = book.title.casefold()
        if title not in seen:
            seen.add(title)
            unique.append(book)
    return unique


def search(books, query="", limit=DEFAULT_LIMIT, after=None):
    if limit <= 0:
        raise ValueError("limit must be positive")

    matches = [book for book in books if _matches(book, query)]
    matches = _dedupe_titles(matches)
    matches.sort(key=_sort_key)

    if after is not None:
        matches = [book for book in matches if _sort_key(book) > after]

    page = matches[:limit]
    next_cursor = _sort_key(page[-1]) if len(matches) > limit else None
    return {"items": page, "next_cursor": next_cursor}
