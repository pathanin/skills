from .gtfs import load_schedule
from .predict import DEFAULT_HORIZON, upcoming


def stop_board(feed_path, stop_id, now, horizon=DEFAULT_HORIZON):
    """What the passenger-facing board shows at ``now``."""
    schedule = load_schedule(feed_path, now.date())
    return upcoming([schedule], stop_id, now, horizon)
