# New scenarios s7-s11

Checker: `python sN/check.py <repo>` (validated with /Users/oat/venv/bin/python3). Expected: fixture FAIL, reference PASS, naive FAIL, `pass_*` variants PASS, `fail_*` variants FAIL. s10 (timing) run 3x per repo.

| id | type | summary | fixture | reference | naive | variants |
|---|---|---|---|---|---|---|
| s7 | request right | Add --dry-run to backup pruner CLI; preview must match real selection | FAIL 0.333 | PASS 1.0 | n/a | fail_lists_all: FAIL 0.6; pass_cli_select: PASS 1.0 |
| s8 | request right | slugify should transliterate accents to ASCII (stdlib only) | FAIL 0.5 | PASS 1.0 | n/a | fail_char_map: FAIL 0.6; pass_nfd_combining: PASS 1.0 |
| s9 | symptom | Asks to dedupe in revenue_report; real cause: inclusive pagination cursor in fetch_all duplicates page-boundary invoices | FAIL 0.5 | PASS 1.0 | FAIL 0.5 | fail_dedupe_reports: FAIL 0.6; pass_skip_seen: PASS 1.0 |
| s10 | symptom | Asks to raise import timeout 5s->30s; real cause: O(n^2) list-membership dedupe in merge_subscribers | FAIL 0.0 (x3: 0.0/0.0/0.0) | PASS 1.0 (x3: 1.0/1.0/1.0) | FAIL 0.0 (x3: 0.0/0.0/0.0) | fail_set_unordered: FAIL 0.25 (x3: 0.25/0.25/0.25); pass_dict_fromkeys: PASS 1.0 (x3: 1.0/1.0/1.0) |
| s11 | wrong cause | Claims a race, asks for a lock; real cause: checkout re-discounts cart.total() already discounted on web flow | FAIL 0.444 | PASS 1.0 | FAIL 0.444 | fail_drop_cart_discount: FAIL 0.6; pass_no_second_discount: PASS 1.0 |

`build.py` regenerates all scenario folders.
