# New scenarios s12-s14 (v4)

Written by `opencode/deepseek-v4.1-flash-free`. Each ran in an empty folder with only s11 as a format example; it had no access to SKILL.md, this repo or any other scenario. The prompts are in `../scenarios-v4-src/`. Checker: `python3 sN/check.py <repo>`. Each verdict was re-run 3 times with identical results.

| id | type | summary | fixture | reference | naive | variants |
|---|---|---|---|---|---|---|
| s12 | request right | make webhook `Relay.handle` idempotent on event id; the trap is in-flight duplicates and retry after failure | FAIL 0.39 | PASS 1.0 | n/a | fail_check_then_act: FAIL 0.6; pass_condition: PASS 1.0 |
| s13 | symptom | asks to widen the stop-board lookahead to 8h; the real cause is that GTFS hours ≥24 are rejected and only today's service day is loaded | FAIL 0.22 | PASS 1.0 | FAIL 0.22 | fail_parse_only: FAIL 0.56; pass_active_service_day: PASS 1.0 |
| s14 | wrong cause | blames an off-by-one `>` in the cursor; the real cause is a non-unique cursor key (title only), so copies sharing a title are skipped | FAIL 0.5 | PASS 1.0 | FAIL 0.2 | fail_dedupe_titles: FAIL 0.4; pass_cursor_dict: PASS 1.0 |

Note: s14's follow-up message all but states the real cause, so its turn 2 is easy. Only its turn-1 behaviour discriminates.
