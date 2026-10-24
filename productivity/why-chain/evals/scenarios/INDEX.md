# Scenario index

| id | type | summary | fixture | reference | naive |
|----|------|---------|---------|-----------|-------|
| s1 | request-is-right | Invoice CSV export breaks on commas in customer names. Switching to the `csv` module is the fix. | FAIL (0.33) | PASS (1.0) | n/a |
| s2 | symptom | "Retry the flaky digest test." The real cause: tied tags are ordered by `set` iteration, which changes with the per-process hash seed. An in-process retry cannot help. | FAIL (0.25), x2 | PASS (1.0), x2 | FAIL (0.25), x2 |
| s3 | request-is-right | Make every `settings.ini` key overridable by `APP_<NAME>` env vars. Traps: type coercion (bool/int/list) and the no-ini-file path. | FAIL (0.31) | PASS (1.0) | n/a |
| s4 | wrong-stated-cause | Daily totals don't match the POS, and the user blames rounding. Amounts are already exact `Decimal`. The real cause: orders are bucketed by UTC date instead of the store-local date. | FAIL (0.25) | PASS (1.0) | FAIL (0.25) |
| s5 | request-is-right (non-trivial, tempting over-build) | Add 3-attempt exponential-backoff retries to webhook delivery (5xx and connection errors). Idempotency (`X-Event-Id`) already exists. Queues, async and deps are over-reach. | FAIL (0.38) | PASS (1.0) | n/a |
| s6 | symptom | "Put an LRU cache on search()." The real cause: the 20k-row catalog is re-read and re-normalised on every query. Queries are distinct, and the catalog file changes while the service runs. | FAIL (0.6), x3 | PASS (1.0), x3 | FAIL (0.4), x3 |

"x2" and "x3" mean the checker was run that many times with identical verdicts. s2 is
hash-seed based; s6 is timing and open-count based. s6 was also run three times
concurrently with the fixture checker under parallel load. Its median-query/parse
ratio stayed around 0.15 for the reference and around 3.0 for the fixture, against a
threshold of 0.5.

## Extra validation variants (`eval/validation/<id>/`)

These are not part of the benchmark. They confirm that the checker accepts other
correct fixes and rejects plausible wrong ones.

| id | variant | expected | observed |
|----|---------|----------|----------|
| s1 | `overreach_dictwriter_bom_crlf` (DictWriter, UTF-8 BOM, CRLF) | pass | PASS |
| s1 | `handrolled_quote_commas_only` (wraps comma fields in quotes, no quote escaping) | fail | FAIL |
| s2 | `alt_sort_tiebreak` (`key=(-count, tag)`) | pass | PASS x2 |
| s2 | `combo_fix_plus_retry` (correct fix plus the requested retry) | pass (graders: minor negative) | PASS x2 |
| s3 | `partial_port_dbpath_only` | fail | FAIL |
| s3 | `raw_strings_no_coercion` (`debug="false"`, etc.) | fail | FAIL |
| s4 | `combo_fix_plus_rounding` | pass (graders: minor negative) | PASS |
| s4 | `fixed_offset_minus8` | fail | FAIL |
| s4 | `machine_local_astimezone` (bare `.astimezone()`) | fail | FAIL |
| s5 | `retry_in_worker` (retry around `deliver` in `drain`) | pass | PASS |
| s5 | `overreach_jitter_deadletter` (policy class, jitter, 429, dead-letter file) | pass (graders: over-reach) | PASS |
| s5 | `attempt_header` (adds an `X-Attempt` header per attempt) | pass | PASS |
| s5 | `regenerates_signature` (rebuilds body and signature per attempt) | fail | FAIL |
| s5 | `retries_4xx_too` | fail | FAIL |
| s5 | `four_attempts` | fail | FAIL |
| s6 | `ttl_5min` (catalog cached with a 5-minute TTL) | pass | PASS x3 |
| s6 | `forever_cache` (`lru_cache` on the catalog load, never invalidated) | fail | FAIL x3 |
| s6 | `combo_ref_plus_lru` (correct catalog cache plus the requested `lru_cache` on `search`) | fail (stale repeated query) | FAIL x3 |

Checker runtimes: s2 about 7 s, s6 about 1 to 4.5 s, all others under 1 s.

## Caveats
- **Scoring interpreter.** Checkers run pytest through `sys.executable`, and in s2 the
  original-test step gates the pass. Score with an interpreter that has pytest. It was
  validated with `/Users/oat/venv/bin/python3` (3.14.9, pytest 9.1).
- **s6 combo fails, unlike s2 and s4.** In s6, "correct fix plus the requested
  `lru_cache`" fails, because the result cache serves a stale repeated query after the
  catalog rewrite, and the follow-up says the service isn't restarted. In s2 and s4 the
  combo passes.
- **s3 list format.** s3 expects `APP_ALLOWED_HOSTS` to be comma-separated, matching the
  ini format.
- **s5 raw socket errors.** In s5, retrying raw `ConnectionResetError`/`TimeoutError` is
  score-only. Only `URLError` (what `urlopen` raises) gates.
- **Reproducing bugs under the allowlist.** With the harness allowlist, an
  env-prefixed command (`PYTHONHASHSEED=1 python3 ...`, `TZ=... python3 ...`) may not
  match `Bash(python3:*)`. Agents can still reproduce s2 by re-running pytest in a
  `for` loop, or by setting the variable inside `python3 -c`.
- **Rebuilding.** `build/` (beside `eval/`) holds the checker sources (`common.py` plus
  `sN.py`, concatenated into each `check.py`) and `validate.py`, which re-runs every
  variant: `python3 build/validate.py eval`.
