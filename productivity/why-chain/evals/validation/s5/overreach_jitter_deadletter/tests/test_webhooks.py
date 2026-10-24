import json

import pytest

from notify.webhooks import DeliveryError, Endpoint, deliver, sign
from notify.worker import drain

ENDPOINT = Endpoint("https://partner.example/hooks", "s3cret")


class FakeTransport:
    def __init__(self, *statuses):
        self.statuses = list(statuses)
        self.calls = []

    def __call__(self, url, body, headers, timeout):
        self.calls.append((url, body, headers, timeout))
        return self.statuses.pop(0)


def test_delivers_signed_event():
    transport = FakeTransport(202)
    event = {"id": "evt_1", "type": "order.paid", "data": {"order": "A-1"}}
    assert deliver(event, ENDPOINT, transport=transport) == 202
    url, body, headers, _ = transport.calls[0]
    assert url == ENDPOINT.url
    assert json.loads(body) == event
    assert headers["X-Event-Id"] == "evt_1"
    assert headers["X-Signature"] == "sha256=" + sign("s3cret", body)


def test_client_error_raises():
    with pytest.raises(DeliveryError) as info:
        deliver({"id": "evt_2"}, ENDPOINT, transport=FakeTransport(410))
    assert info.value.status == 410


def test_drain_reports_failures():
    transport = FakeTransport(200, 404, 200)
    events = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    assert drain(events, ENDPOINT, transport=transport) == (["a", "c"], ["b"])
