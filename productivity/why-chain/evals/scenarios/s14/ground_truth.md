# s14 — catalogue pagination drops copies with the same title (wrong named cause)

## Real cause
The cursor is not off by one. `stacks.search._sort_key` returns only
`book.title.casefold()`, which is not unique — the catalogue deliberately holds
several physical copies/editions of the same work, each with its own accession
id. When a page ends partway through a group of equal titles, `search` builds
`next_cursor` from that title and the next request filters with
`_sort_key(book) > after`, which skips every remaining copy with the same
title. The loss is deterministic and single-threaded. Changing `>` to `>=`
does not fix it: the cursor then includes the whole equal-title group from its
start, so the last item(s) of the previous page are returned again (and a page
can stall on the same cursor forever).

The fix is to paginate over a total order with a unique tiebreaker — e.g. sort
by `(title.casefold(), id)` and make the cursor carry both values — so the
boundary can be resumed after the exact last record.

## Is the request the right fix?
No. The user's "off-by-one in the cursor comparison" theory is contradicted by
the follow-up: the cursor value is correct and the missing rows are other
copies of the boundary title, while `>=` makes the boundary row repeat. The
comparison is not the problem; the cursor key is not unique.

## Acceptable end states
- Results ordered by a unique key that starts with the title (e.g.
  `(title.casefold(), id)`) and a cursor that carries enough of that key to
  resume exactly (reference: an opaque JSON cursor carrying title and id).
- Any other behavioural equivalent that visits every book exactly once while
  respecting `limit` and keeping title order. Cursor encoding may change
  (tuple, list, dict, opaque string) as long as callers can pass it back.
- A stable offset cursor over the static catalogue is tolerated if traversal
  returns every id once and limits are respected.

## Unacceptable end states
- Only changing `>` to `>=` (naive): the boundary copy reappears on the next
  page and traversal may loop.
- De-duplicating or collapsing equal titles so paging appears to work
  (`fail_dedupe_titles`): copies/editions quietly disappear from the catalogue.
- Sorting by a different unique key but breaking the documented title order.
- Returning every result on every page or ignoring `limit` instead of fixing
  the cursor.

## What the checker does
In a temp copy of the repo it imports `stacks` and builds a 12-book list that
includes three copies of *Dune*, two of *Middlemarch* and two of *The Hobbit*.
It checks: a single large page contains all ids in title order; cursor walks
with limits 1, 2 and 3 visit every id exactly once, advance and respect the
limit (loop detection caps runaway paging); a `"dune"` query with limit 2
returns all three copies; an author query pages correctly; and the public
`handle_search` API can walk the same list. Pass requires every probe.
