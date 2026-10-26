from datetime import timedelta

from .gtfs import load_schedule
from .predict import DEFAULT_HORIZON, upcoming

# The agency runs one service day from 03:00 until 02:59 the next morning.
SERVICE_DAY_ROLLOVER_HOUR = 3


def stop_board(feed_path, stop_id, now, horizon=DEFAULT_HORIZON):
    """What the passenger-facing board shows at ``now``."""
    service_date = now.date()
    if now.hour < SERVICE_DAY_ROLLOVER_HOUR:
        service_date -= timedelta(days=1)
    schedule = load_schedule(feed_path, service_date)
    return upcoming([schedule], stop_id, now, horizon)
