from datetime import timedelta

from .gtfs import load_schedule
from .predict import DEFAULT_HORIZON, upcoming


def stop_board(feed_path, stop_id, now, horizon=DEFAULT_HORIZON):
    """What the passenger-facing board shows at ``now``.

    Around midnight the previous service day is still running, so its 24:xx
    and 25:xx trips have to be considered too.
    """
    schedules = [
        load_schedule(feed_path, now.date() - timedelta(days=1)),
        load_schedule(feed_path, now.date()),
    ]
    return upcoming(schedules, stop_id, now, horizon)
