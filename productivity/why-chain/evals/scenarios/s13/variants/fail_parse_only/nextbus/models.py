from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Trip:
    trip_id: str
    route_id: str
    stop_id: str
    arrival: datetime


@dataclass(frozen=True)
class Arrival:
    trip_id: str
    route_id: str
    stop_id: str
    when: datetime
