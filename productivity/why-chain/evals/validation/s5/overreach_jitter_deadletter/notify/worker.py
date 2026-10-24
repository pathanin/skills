import json
import logging
from pathlib import Path

from notify.webhooks import DeliveryError, Endpoint, Transport, deliver, post_json

log = logging.getLogger(__name__)


def drain(events: list[dict], endpoint: Endpoint, transport: Transport = post_json) -> tuple[list[str], list[str]]:
    """Deliver queued events in order. Returns (delivered_ids, failed_ids)."""
    delivered, failed = [], []
    for event in events:
        try:
            deliver(event, endpoint, transport=transport)
        except (DeliveryError, OSError) as exc:
            log.warning("could not deliver %s: %s", event["id"], exc)
            failed.append(event["id"])
            with open(Path("dead_letter.jsonl"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"event": event, "error": str(exc)}) + "\n")
        else:
            delivered.append(event["id"])
    return delivered, failed
