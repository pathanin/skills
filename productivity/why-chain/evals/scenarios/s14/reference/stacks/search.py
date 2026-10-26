"""Catalogue search with cursor pagination.

The public contract is a dict with ``items`` (a page of Book objects) and
``next_cursor`` (pass it back as ``after`` to fetch the next page, or None
when there are no more results).
"""

import json

DEFAULT_LIMIT = 10


def _matches(book, query):
    needle = query.strip().casefold()
    if not needle:
        return True
    return needle in book.title.casefold() or needle in book.author.casefold()


def _sort_key(book):
    # Title is the primary order, but it is not unique: the catalogue holds
    # several copies/editions of the same work. The accession id breaks ties
    # so a page boundary can always be resumed after one exact record.
    return (book.title.casefold(), book.id)


def _cursor_key(after):
    if isinstance(after, str):
        try:
            after = json.loads(after)
        except ValueError:
            return (after.casefold(), "")
    if isinstance(after, (tuple, list)) and len(after) >= 2:
        return (str(after[0]).casefold(), str(after[1]))
    return (str(after).casefold(), "")


def _encode_cursor(book):
    # Keep the cursor opaque to callers and JSON-safe for the API wrapper.
    return json.dumps([book.title, book.id])


def search(books, query="", limit=DEFAULT_LIMIT, after=None):
    if limit <= 0:
        raise ValueError("limit must be positive")

    matches = [book for book in books if _matches(book, query)]
    matches.sort(key=_sort_key)

    if after is not None:
        cursor = _cursor_key(after)
        matches = [book for book in matches if _sort_key(book) > cursor]

    page = matches[:limit]
    next_cursor = _encode_cursor(page[-1]) if len(matches) > limit else None
    return {"items": page, "next_cursor": next_cursor}
