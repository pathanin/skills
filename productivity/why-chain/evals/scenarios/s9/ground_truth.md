# s9 — revenue report overcounts (symptom)

## Real cause
`fetch.fetch_all` pages with `cursor = page[-1].id`, but the API's `starting_at` is inclusive (documented in `InvoiceAPI`'s docstring and implemented with `>=`). The last invoice of each full page is fetched again as the first of the next page, so every page boundary duplicates one invoice. Every consumer of `fetch_all` is affected, including `customer_totals`.

## Is the request the right fix?
No. Deduping inside `revenue_report` hides the symptom in one report while `fetch_all` still returns duplicates and `customer_totals` still overstates customer spend.

## Acceptable end states
- `fetch_all` returns each invoice exactly once (e.g. `cursor = page[-1].id + 1`, or skipping ids <= last seen — variant `pass_skip_seen`), for any page size.
- Deduping inside `revenue_report` as well is harmless if `fetch_all` is fixed.

## Unacceptable end states
- Dedupe only in `revenue_report` (naive).
- Dedupe in each report but `fetch_all` still duplicates (`fail_dedupe_reports`).
- Changing the API stand-in's semantics so tests pass while the real service contract (inclusive) is ignored is questionable; the checker uses the fixture's own `InvoiceAPI` from the repo, so it would pass, but ground truth treats the fetch side as the real fix.

## What the checker does
Imports the package from a temp copy, builds 350 invoices with non-contiguous ids, and checks `fetch_all` returns exactly the ids once each with default page size and page sizes 50, 7, 3; then checks `revenue_report` and `customer_totals` totals and a 5-invoice case. Pass requires all.
