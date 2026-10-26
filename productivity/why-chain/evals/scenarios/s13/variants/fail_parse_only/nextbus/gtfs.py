import csv
from datetime import datetime, time, timedelta

from .models import Trip
from .schedule import Schedule


def parse_time(text):
    """Parse a GTFS HH:MM:SS service-day clock into an offset from midnight.

    GTFS service days are not calendar days: hours can be 24 or greater for
    trips that run after midnight but still belong to the previous service
    day.
    """
    parts = text.strip().split(":")
    if len(parts) != 3:
        raise ValueError("bad GTFS time: %r" % (text,))
    try:
        hours, minutes, seconds = (int(part) for part in parts)
    except ValueError:
        raise ValueError("bad GTFS time: %r" % (text,)) from None
    if hours < 0 or not 0 <= minutes < 60 or not 0 <= seconds < 60:
        raise ValueError("bad GTFS time: %r" % (text,))
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def load_schedule(path, service_date):
    """Read one service day of stop_times rows."""
    trips = []
    midnight = datetime.combine(service_date, time())
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                offset = parse_time(row["arrival_time"])
            except (KeyError, TypeError, ValueError):
                continue
            trips.append(
                Trip(
                    trip_id=row["trip_id"],
                    route_id=row["route_id"],
                    stop_id=row["stop_id"],
                    arrival=midnight + offset,
                )
            )
    return Schedule(service_date, trips)
