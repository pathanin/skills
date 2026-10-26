from datetime import datetime, timedelta
from pathlib import Path

from nextbus.board import stop_board

FEED = Path(__file__).resolve().parents[1] / "data" / "stop_times.csv"


def test_late_night_trips_before_midnight():
    board = stop_board(
        FEED,
        "CENTRAL",
        datetime(2026, 5, 4, 23, 30),
        horizon=timedelta(hours=2),
    )
    assert [arrival.trip_id for arrival in board] == [
        "9-2340",
        "N9-2400",
        "N9-2415",
        "N9-2505",
    ]


def test_previous_service_day_after_midnight():
    board = stop_board(
        FEED,
        "CENTRAL",
        datetime(2026, 5, 5, 0, 5),
        horizon=timedelta(hours=2),
    )
    assert [arrival.trip_id for arrival in board] == ["N9-2415", "N9-2505"]
    assert [arrival.when for arrival in board] == [
        datetime(2026, 5, 5, 0, 15),
        datetime(2026, 5, 5, 1, 5),
    ]
