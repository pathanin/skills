import pytest

from hookrelay.events import Event
from hookrelay.handlers import HandlerRegistry, UnknownEventType, default_registry


def test_default_registry_handles_ping():
    registry = default_registry()
    receipt = registry.handler_for("ping")(Event("evt_1", "ping", {}))
    assert receipt == {"pong": True}


def test_default_registry_handles_deploy():
    registry = default_registry()
    result = registry.handler_for("deploy")(
        Event("evt_2", "deploy", {"service": "api"})
    )
    assert result == {"service": "api", "status": "queued"}


def test_unknown_type_raises():
    registry = default_registry()
    assert registry.types() == ["deploy", "ping"]
    with pytest.raises(UnknownEventType):
        registry.handler_for("nope")


def test_register_replaces_handler():
    registry = HandlerRegistry()
    registry.register("ping", lambda event: {"pong": False})
    assert registry.handler_for("ping")(Event("evt_3", "ping", {})) == {"pong": False}
