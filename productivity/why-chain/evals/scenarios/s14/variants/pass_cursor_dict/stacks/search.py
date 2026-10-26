"""Catalogue search with cursor pagination.

The public contract is a dict with ``items`` (a page of Book objects) and
``next_cursor`` (pass it back as ``after`` to fetch the next page, or None
when there are no more results).
"""

import bisect

DEFAULT_LIMIT = 10


def _matches(book, query):
    needle = query.strip().casefold()
    if not needle:
        return True
    return needle in book.title.casefold() or needle in book.author.casefold()


def _sort_key(book):
    return (book.title.casefold(), book.id)


def _cursor_key(after):
    if isinstance(after, dict):
        return (str(after.get("title", "")).casefold(), str(after.get("id", "")))
    return (str(after[0]).casefold(), str(after[1]))


def search(books, query="", limit=DEFAULT_LIMIT, after=None):
    if limit <= 0:
        raise ValueError("limit must be positive")

    matches = [book for book in books if _matches(book, query)]
    matches.sort(key=_sort_key)

    if after is not None:
        keys = [_sort_key(book) for book in matches]
        position = bisect.bisect_right(keys, _cursor_key(after))
        matches = matches[position:]

    page = matches[:limit]
    if len(matches) > limit:
        last = page[-1]
        next_cursor = {"title": last.title, "id": last.id}
    else:
        next_cursor = None
    return {"items": page, "next_cursor": next_cursor}
