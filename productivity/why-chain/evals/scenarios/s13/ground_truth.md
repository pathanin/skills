# s13 — late-night bus trips missing (symptom)

## Real cause
Two related bugs, neither of them in the lookahead window:

1. GTFS `arrival_time` is a service-day clock, so trips after midnight are encoded as `24:15:00`, `25:05:00`, and so on. `nextbus.gtfs.parse_time` uses `datetime.strptime(text, "%H:%M:%S")`, which rejects any hour of 24 or more, and `load_schedule` silently skips those rows. Every N9 trip is discarded while the feed is loaded.
2. `nextbus.board.stop_board` only loads `now.date()`'s schedule. After midnight the trips still running belong to the previous service day (the ones encoded as 24:xx/25:xx), so even a correct parser never sees them unless the board also loads `now.date() - 1 day`.

At 23:30 the existing two-hour window already covers 24:00, 24:15, and 25:05 (00:00, 00:15, and 01:05), so the size of the window is not the problem.

## Is the request the right fix?
No. A wider horizon cannot recover rows that were thrown away during parsing, and after midnight it cannot reach a service day that is never loaded. `parse_time` and `stop_board` need fixing.

## Acceptable end states
- Parse service-day clocks as an offset from midnight (`timedelta`, seconds, etc.) and add that offset to the service date, so 24:15 and 25:05 become 00:15 and 01:05 on the next calendar day.
- Around midnight, consider the previous service day as well as the current one (the reference loads both; `pass_active_service_day` selects the active service day with a 03:00 rollover).
- Late trips appear both before and after midnight, sorted, stop-filtered, and still respect the caller's horizon; daytime behaviour is unchanged.
- Malformed clocks are skipped without taking the board down.

## Unacceptable end states
- Only increasing the lookahead (naive): the N9 rows are still dropped at parse time.
- Fixing the parser but continuing to load only today's service day (`fail_parse_only`): works at 23:30, empty after midnight.
- Wrapping 24:xx to 00:xx on the same service date: the trip lands in the past and disappears.
- Hardcoding the N9 trip ids or a fixed 24:15/25:05 offset.
- Loading yesterday's schedule and shifting every trip forward a day, producing wrong times or duplicates.

## What the checker does
In a temp copy it writes a synthetic stop_times feed and calls `nextbus.board.stop_board` at fixed naive datetimes: daytime, 23:30, 23:45, 23:50, and 00:05 the next day, with different stops and horizons. It requires the core cases (the 24:00, 24:15, and 25:05 trips from the current/previous service day to appear at the right absolute times, no past trips, horizon respected, stop filter) and awards extra score for ignoring malformed clock values.
