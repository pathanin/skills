from datetime import date, datetime, timedelta

from nextbus.gtfs import load_schedule
from nextbus.predict import upcoming


def _feed(tmp_path):
    path = tmp_path / "stop_times.csv"
    path.write_text(
        "trip_id,route_id,stop_id,arrival_time\n"
        "a,1,MAIN,09:05:00\n"
        "b,1,MAIN,09:45:00\n"
        "c,1,OTHER,09:05:00\n",
        encoding="utf-8",
    )
    return path


def test_horizon_filters(tmp_path):
    schedule = load_schedule(_feed(tmp_path), date(2026, 5, 4))
    found = upcoming(
        [schedule],
        "MAIN",
        datetime(2026, 5, 4, 9, 0),
        horizon=timedelta(minutes=30),
    )
    assert [arrival.trip_id for arrival in found] == ["a"]


def test_sorted_by_time(tmp_path):
    schedule = load_schedule(_feed(tmp_path), date(2026, 5, 4))
    found = upcoming(
        [schedule],
        "MAIN",
        datetime(2026, 5, 4, 9, 0),
        horizon=timedelta(hours=1),
    )
    assert [arrival.trip_id for arrival in found] == ["a", "b"]
