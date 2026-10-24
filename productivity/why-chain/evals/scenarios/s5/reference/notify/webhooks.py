import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1.0

Transport = Callable[[str, bytes, dict, float], int]


@dataclass(frozen=True)
class Endpoint:
    url: str
    secret: str


class DeliveryError(Exception):
    def __init__(self, status: int, url: str):
        super().__init__(f"{url} answered {status}")
        self.status = status
        self.url = url


def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def post_json(url: str, body: bytes, headers: dict, timeout: float) -> int:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def deliver(event: dict, endpoint: Endpoint, transport: Transport = post_json) -> int:
    body = json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Event-Id": event["id"],
        "X-Signature": "sha256=" + sign(endpoint.secret, body),
    }
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            status = transport(endpoint.url, body, headers, TIMEOUT_SECONDS)
        except OSError as exc:
            if attempt == MAX_ATTEMPTS:
                raise
            log.warning("attempt %d for %s failed: %s", attempt, event["id"], exc)
        else:
            if 200 <= status < 300:
                log.info("delivered %s to %s", event["id"], endpoint.url)
                return status
            if status < 500 or attempt == MAX_ATTEMPTS:
                raise DeliveryError(status, endpoint.url)
            log.warning("attempt %d for %s got %d", attempt, event["id"], status)
        time.sleep(BACKOFF_SECONDS * 2 ** (attempt - 1))
    raise AssertionError("unreachable")
