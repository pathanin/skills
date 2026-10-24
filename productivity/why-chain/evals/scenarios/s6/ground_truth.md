# s6: slow product search (symptom)

## Real cause
`shop/search.py::search` calls `load_catalog(config.CATALOG_PATH)` on **every query**.
That re-opens and re-parses the whole CSV (about 20k rows) and re-normalises every
product name with `unicodedata`, before scanning. Locally that is ~80 ms per query,
about 4x the cost of a bare CSV parse. The actual scan over pre-normalised strings
takes ~3 ms.

## Is the request the right fix?
No. An LRU cache on `search(query)` only helps when the exact same query repeats.
The follow-up says queries are almost all distinct and slow on first use, so the cache
changes nothing for users. It also introduces staleness: a cached query keeps returning
old results after the ERP rewrites the catalog, because the service is not restarted.

## Acceptable end states
- Parse and normalise the catalog once and keep it in memory. Each query only scans
  (or uses an index). And:
- Pick up catalog rewrites without a restart, either:
  - by checking the file's mtime (or size and mtime) on each query and reloading when
    it changes (the reference), or
  - by a time-based refresh no longer than about an hour.
- Building an inverted index or similar is fine but not needed. The plain scan over
  cached data is ~25x faster than the fixture.
- Keeping an LRU cache *on top of* a correct catalog cache passes the checker only if it
  is invalidated when the catalog reloads. Otherwise the repeated-query freshness check
  fails. Graders should treat an extra result cache as unnecessary.
- Tests continue to work when `config.CATALOG_PATH` is monkeypatched per test. The cache
  should be keyed by path, or reset.

## Unacceptable end states
- `@lru_cache` on `search` (naive): distinct queries are still slow, and repeated
  queries go stale after an ERP rewrite.
- Caching the catalog forever (module import, or `lru_cache` on `load_catalog` with no
  invalidation): fast, but serves a stale catalog until the next restart. The checker's
  freshness step fails it.
- Changing search semantics (ranking, accent folding, all-terms matching, limit) to make
  it faster.
- Pre-converting the CSV to a pickle/sqlite file that is still read on every query.

## What the checker does
Generates a 20,000-product catalog with accented names, then runs 41 distinct queries
in a fresh interpreter. It:
- compares results to an oracle of the original algorithm;
- counts opens of `catalog.csv` with an audit hook, and requires 2 or fewer for all
  41 queries;
- requires the median per-query time to be below half of one bare `csv.DictReader`
  parse of the file, measured in the same process (fixture ~4x, reference ~0.15x);
- rewrites the catalog with a new top-ranked product matching the *first* query,
  moves the wall clocks (`time.time`, `time.monotonic`, `datetime.now`) forward one
  hour, and requires both that repeated query and a new query to return the new product.

The repo's own tests count toward the score only.
