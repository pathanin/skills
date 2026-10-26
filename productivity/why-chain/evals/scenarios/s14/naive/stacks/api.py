"""Thin request/response wrapper around Catalog.search."""

DEFAULT_LIMIT = 10


def handle_search(catalog, params):
    """Handle a catalogue search request.

    ``params`` mirrors the public query string: ``q``, ``limit`` and
    ``after``. The returned cursor is opaque to clients; hand it back in the
    next request unchanged.
    """
    try:
        limit = int(params.get("limit", DEFAULT_LIMIT))
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT

    page = catalog.search(
        query=params.get("q", ""),
        limit=limit,
        after=params.get("after"),
    )
    return {
        "items": [book.as_dict() for book in page["items"]],
        "next_cursor": page["next_cursor"],
    }
