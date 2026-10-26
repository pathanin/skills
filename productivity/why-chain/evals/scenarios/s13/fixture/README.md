# nextbus

Stop-board service for a small bus agency. It reads a GTFS-style
`stop_times.csv` and answers "what is leaving this stop in the next N hours?"

- `nextbus.gtfs.load_schedule(path, service_date)` reads the feed for one
  service day. `arrival_time` is the GTFS service-day clock (`HH:MM:SS`,
  measured from the start of the service day).
- `nextbus.predict.upcoming(schedules, stop_id, now, horizon)` filters
  schedules by stop and lookahead window.
- `nextbus.board.stop_board(path, stop_id, now, horizon=...)` is what the
  passenger-facing board calls.

The sample feed in `data/stop_times.csv` has route 9 daytime service and the
N9 night service.
