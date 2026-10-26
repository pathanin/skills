from datetime import datetime, timedelta
from pathlib import Path

from nextbus.board import stop_board

FEED = Path(__file__).resolve().parents[1] / "data" / "stop_times.csv"


def test_morning_board():
    board = stop_board(FEED, "CENTRAL", datetime(2026, 5, 4, 8, 0))
    assert [arrival.trip_id for arrival in board] == ["9-0810", "9-0830", "9-0900"]


def test_stop_filter():
    board = stop_board(FEED, "RIVERSIDE", datetime(2026, 5, 4, 8, 0))
    assert [arrival.trip_id for arrival in board] == ["9-0820", "9-0850"]


def test_horizon():
    board = stop_board(
        FEED,
        "CENTRAL",
        datetime(2026, 5, 4, 8, 0),
        horizon=timedelta(minutes=45),
    )
    assert [arrival.trip_id for arrival in board] == ["9-0810", "9-0830"]
