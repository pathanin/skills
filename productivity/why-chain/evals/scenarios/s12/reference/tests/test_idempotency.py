import threading
import time

import pytest

from hookrelay.events import Event
from hookrelay.handlers import HandlerRegistry
from hookrelay.relay import Relay


def test_duplicate_delivery_returns_original_receipt():
    calls = []

    def handler(event):
        calls.append(event.id)
        return {"n": len(calls)}

    registry = HandlerRegistry()
    registry.register("ping", handler)
    relay = Relay(registry=registry)
    event = Event("evt_1", "ping", {})

    first = relay.handle(event)
    second = relay.handle(event)

    assert calls == ["evt_1"]
    assert second == first
    assert relay.stats.count_for("ping") == 1


def test_failed_delivery_is_retried_and_then_cached():
    attempts = []

    def flaky(event):
        attempts.append(1)
        if len(attempts) < 2:
            raise RuntimeError("downstream is down")
        return {"attempt": len(attempts)}

    registry = HandlerRegistry()
    registry.register("flaky", flaky)
    relay = Relay(registry=registry)
    event = Event("evt_2", "flaky", {})

    with pytest.raises(RuntimeError):
        relay.handle(event)
    assert relay.receipts.get("evt_2") is None

    receipt = relay.handle(event)
    assert receipt.result == {"attempt": 2}

    assert relay.handle(event) == receipt
    assert len(attempts) == 2


def test_concurrent_duplicate_runs_handler_once():
    started = threading.Event()
    release = threading.Event()
    calls = []

    def slow(event):
        calls.append(1)
        call_number = len(calls)
        started.set()
        assert release.wait(5)
        return {"call": call_number}

    registry = HandlerRegistry()
    registry.register("slow", slow)
    relay = Relay(registry=registry)
    event = Event("evt_3", "slow", {})
    results = []
    errors = []

    def worker():
        try:
            results.append(relay.handle(event))
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    first = threading.Thread(target=worker)
    first.start()
    assert started.wait(5)
    second = threading.Thread(target=worker)
    second.start()
    time.sleep(0.2)
    release.set()
    first.join(5)
    second.join(5)

    assert errors == []
    assert calls == [1]
    assert len(results) == 2
    assert results[0] == results[1]
