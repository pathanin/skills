from datetime import timedelta

from .models import Arrival
from .schedule import Schedule

DEFAULT_HORIZON = timedelta(hours=2)


def upcoming(schedules, stop_id, now, horizon=DEFAULT_HORIZON):
    """Return arrivals at stop_id in [now, now + horizon], soonest first."""
    if isinstance(schedules, Schedule):
        schedules = [schedules]
    cutoff = now + horizon
    found = []
    for schedule in schedules:
        for trip in schedule.trips:
            if trip.stop_id != stop_id:
                continue
            if now <= trip.arrival <= cutoff:
                found.append(
                    Arrival(
                        trip_id=trip.trip_id,
                        route_id=trip.route_id,
                        stop_id=trip.stop_id,
                        when=trip.arrival,
                    )
                )
    found.sort(key=lambda arrival: (arrival.when, arrival.trip_id))
    return found
