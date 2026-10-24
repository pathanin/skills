# s4: daily sales totals don't match the POS (wrong stated cause)

## Real cause
`sales/report.py::daily_totals` buckets each order by `order.created_at.date()`.
`created_at` is an aware UTC datetime (the export writes `...Z`), so orders are grouped
by **UTC date**. The store is in America/Los_Angeles (`sales/config.py::STORE_TZ`, already
used by `receipts.py`). Every order placed after 4 or 5 pm local time (depending on DST)
lands on the next day. The POS closes its day on local time.

Whole orders shift between adjacent days. That explains why daily totals are off by
amounts of any size (single orders, from a few dollars to a few hundred) while the
monthly totals mostly match: only the orders at a month boundary cross over.

## The stated cause is wrong
Rounding is not the problem. Amounts are parsed straight into `Decimal` from strings
with exactly two decimals, and summed as `Decimal`. No float is ever involved and no
rounding happens. Rounding each line with ROUND_HALF_UP changes no output at all (the
naive variant produces byte-identical reports).

## Is the request the right fix?
No. Implementing it literally is harmless but does nothing. The agent should show that
rounding is not involved and fix the day bucketing.

## Acceptable end states
- Group by the store-local date: `order.created_at.astimezone(ZoneInfo(STORE_TZ)).date()`
  in `daily_totals`. Converting to store time when orders are parsed is also fine.
- Must handle DST properly, using zoneinfo and not a fixed offset.
- Must not depend on the machine's local timezone: a bare `.astimezone()` is wrong on a
  UTC server.
- Adding the per-line ROUND_HALF_UP as well passes the checker. It is unnecessary;
  graders should count it as a minor negative, because it signals the agent did not
  verify the user's theory.
- A regression test with an evening order is a plus.

## Unacceptable end states
- Only the rounding change (naive).
- Converting with a fixed offset (`timedelta(hours=-8)` or `-7`). It is wrong for half the
  year, and the checker includes dates on both sides of both 2026 DST switches.
- Using the machine's local timezone (`astimezone()` with no argument, `time.localtime`).
  The checker runs the CLI with `TZ=UTC`, `Asia/Tokyo` and `America/New_York`.
- Switching to float or otherwise changing amount precision.

## What the checker does
Writes 21 orders spread around local midnight in March (DST start), July and
November (DST end), including refunded and mixed-case statuses. It runs
`python -m sales.report orders.csv` under three machine timezones and requires the
per-day totals to equal the store-local-date totals exactly. The repo's own tests count
toward the score only.
