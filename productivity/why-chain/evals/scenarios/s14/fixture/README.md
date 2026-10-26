# stacks

Search and cursor pagination for the branch library catalogue service.

The catalogue holds one record per physical copy or edition, so popular
titles appear several times with different accession ids. Search results are
ordered by title.

- `stacks.search.search(books, query="", limit=10, after=None)` is the core
  routine. It returns `{"items": [...], "next_cursor": ...}` where the cursor
  is opaque: callers pass it back as `after`. `None` means there are no more
  pages.
- `stacks.store.Catalog` wraps a list of books for the service.
- `stacks.api.handle_search(catalog, params)` adapts the public query string
  (`q`, `limit`, `after`) and returns JSON-ready dicts.

`stacks.store.DEMO_BOOKS` is a representative slice of the catalogue,
including three copies of *Dune* and two of *Middlemarch*.

Run the tests with:

```sh
python3 -m pytest -q
```
