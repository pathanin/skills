import pytest

from hookrelay.events import Event
from hookrelay.handlers import HandlerRegistry, UnknownEventType
from hookrelay.relay import Relay


def test_ping_is_receipted_and_counted():
    relay = Relay()
    receipt = relay.handle(Event("evt_1", "ping", {}))
    assert receipt.event_id == "evt_1"
    assert receipt.event_type == "ping"
    assert receipt.result == {"pong": True}
    assert relay.receipts.get("evt_1") == receipt
    assert relay.stats.snapshot() == {"ping": 1}


def test_deploy_receipt():
    relay = Relay()
    receipt = relay.handle(
        Event("evt_2", "deploy", {"service": "worker", "sha": "abc123"})
    )
    assert receipt.result == {"service": "worker", "status": "queued"}


def test_different_events_each_run():
    calls = []

    def handler(event):
        calls.append(event.id)
        return {"n": len(calls)}

    registry = HandlerRegistry()
    registry.register("ping", handler)
    relay = Relay(registry=registry)

    relay.handle(Event("evt_1", "ping", {}))
    relay.handle(Event("evt_2", "ping", {}))

    assert calls == ["evt_1", "evt_2"]
    assert relay.stats.count_for("ping") == 2


def test_unknown_type_does_not_create_a_receipt():
    relay = Relay()
    with pytest.raises(UnknownEventType):
        relay.handle(Event("evt_3", "nope", {}))
    assert relay.receipts.all() == []
    assert relay.stats.snapshot() == {}


def test_handler_failure_is_not_receipted():
    registry = HandlerRegistry()

    def explode(event):
        raise RuntimeError("downstream is down")

    registry.register("boom", explode)
    relay = Relay(registry=registry)

    with pytest.raises(RuntimeError):
        relay.handle(Event("evt_4", "boom", {}))

    assert relay.receipts.get("evt_4") is None
    assert relay.stats.count_for("boom") == 0
