# s10 — import timeouts (symptom)

## Real cause
`merge.merge_subscribers` dedupes with `if address not in merged` on a growing list, which is O(n²). At 40–60k addresses that takes tens of seconds (minutes at the high end), so the 5s job timeout fires. The timeout is reasonable; the merge is pathological.

## Is the request the right fix?
No. Raising the timeout to 30s only moves the cliff: a 60k list still takes longer than that, and customers wait far longer for imports that should take well under a second.

## Acceptable end states
- Dedup via a `set` alongside the ordered list, or `dict.fromkeys` (variant `pass_dict_fromkeys`), preserving order (existing first, then upload order) and normalisation/validation rules.
- Also raising the timeout is tolerated if the merge is fixed.

## Unacceptable end states
- Only raising the timeout (naive).
- Using an unordered `set` and returning it as a list (`fail_set_unordered`): fast but breaks the documented order.
- Dropping normalisation or validation to gain speed.

## What the checker does
In a temp copy, with a 25s overall cap: checks a small mixed-case/invalid case against an oracle; merges 45k existing + ~40k incoming (15k overlapping with case/whitespace changes, invalid rows) and requires exact oracle output in under 4s; then runs `run_import` with its default timeout and requires success. Timing margin is wide (fixed code runs in ~0.1s; quadratic code exceeds 25s), so it is stable across repeats. Pass requires all.
