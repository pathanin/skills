import logging
import time

from notify.webhooks import DeliveryError, Endpoint, Transport, deliver, post_json

log = logging.getLogger(__name__)


def drain(events: list[dict], endpoint: Endpoint, transport: Transport = post_json) -> tuple[list[str], list[str]]:
    """Deliver queued events in order. Returns (delivered_ids, failed_ids)."""
    delivered, failed = [], []
    for event in events:
        try:
            _deliver_with_retries(event, endpoint, transport)
        except (DeliveryError, OSError) as exc:
            log.warning("could not deliver %s: %s", event["id"], exc)
            failed.append(event["id"])
        else:
            delivered.append(event["id"])
    return delivered, failed


def _deliver_with_retries(event, endpoint, transport, attempts=3, base=0.5):
    for attempt in range(attempts):
        try:
            return deliver(event, endpoint, transport=transport)
        except DeliveryError as exc:
            if exc.status < 500 or attempt == attempts - 1:
                raise
        except OSError:
            if attempt == attempts - 1:
                raise
        time.sleep(base * 2 ** attempt)
