import pytest

from hookrelay.events import Event, InvalidEvent, event_from_payload


def test_parses_delivery():
    event = event_from_payload(
        {
            "id": "evt_9f2",
            "type": "deploy",
            "payload": {"service": "api"},
        }
    )
    assert event == Event(id="evt_9f2", type="deploy", payload={"service": "api"})


def test_payload_defaults_to_empty_dict():
    event = event_from_payload({"id": "evt_1", "type": "ping"})
    assert event.payload == {}


def test_requires_id():
    with pytest.raises(InvalidEvent):
        event_from_payload({"type": "ping"})


def test_requires_type():
    with pytest.raises(InvalidEvent):
        event_from_payload({"id": "evt_1"})


def test_rejects_non_object_payload():
    with pytest.raises(InvalidEvent):
        event_from_payload({"id": "evt_1", "type": "ping", "payload": ["nope"]})
