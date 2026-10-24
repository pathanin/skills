import hashlib
import hmac
import json
import logging
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10

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


class RetryPolicy:
    def __init__(self, attempts=3, base=1.0, cap=30.0, retry_statuses=frozenset({429, 500, 502, 503, 504}),
                 sleep=None, rng=None):
        self.attempts, self.base, self.cap = attempts, base, cap
        self.retry_statuses = retry_statuses
        self.sleep = sleep or (lambda s: time.sleep(s))
        self.rng = rng or random.Random()

    def backoff(self, attempt):
        return min(self.cap, self.base * 2 ** attempt) * self.rng.uniform(0.5, 1.0)


DEFAULT_POLICY = RetryPolicy()


def deliver(event: dict, endpoint: Endpoint, transport: Transport = post_json, policy: RetryPolicy | None = None) -> int:
    policy = policy or DEFAULT_POLICY
    body = json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Event-Id": event["id"],
        "X-Signature": "sha256=" + sign(endpoint.secret, body),
    }
    for attempt in range(policy.attempts):
        last = attempt == policy.attempts - 1
        try:
            status = transport(endpoint.url, body, headers, TIMEOUT_SECONDS)
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if last:
                raise
        else:
            if 200 <= status < 300:
                log.info("delivered %s to %s", event["id"], endpoint.url)
                return status
            if status not in policy.retry_statuses and not 500 <= status < 600 or last:
                raise DeliveryError(status, endpoint.url)
        policy.sleep(policy.backoff(attempt))
    raise RuntimeError("unreachable")
