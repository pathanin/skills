from dataclasses import dataclass


class InvalidEvent(ValueError):
    """Raised when a delivery body is not a usable event."""


@dataclass(frozen=True)
class Event:
    id: str
    type: str
    payload: dict


def event_from_payload(body):
    """Turn a decoded delivery body into an Event."""
    if not isinstance(body, dict):
        raise InvalidEvent("event must be a JSON object")

    event_id = body.get("id")
    event_type = body.get("type")
    if not isinstance(event_id, str) or not event_id.strip():
        raise InvalidEvent("event id is required")
    if not isinstance(event_type, str) or not event_type.strip():
        raise InvalidEvent("event type is required")

    payload = body.get("payload")
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise InvalidEvent("payload must be a JSON object")

    return Event(id=event_id, type=event_type, payload=payload)
