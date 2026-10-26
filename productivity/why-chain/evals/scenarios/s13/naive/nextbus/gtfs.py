import csv
from datetime import datetime

from .models import Trip
from .schedule import Schedule


def parse_time(text):
    """Parse a GTFS HH:MM:SS service-day clock."""
    return datetime.strptime(text.strip(), "%H:%M:%S").time()


def load_schedule(path, service_date):
    """Read one service day of stop_times rows."""
    trips = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                clock = parse_time(row["arrival_time"])
            except (KeyError, TypeError, ValueError):
                continue
            trips.append(
                Trip(
                    trip_id=row["trip_id"],
                    route_id=row["route_id"],
                    stop_id=row["stop_id"],
                    arrival=datetime.combine(service_date, clock),
                )
            )
    return Schedule(service_date, trips)
