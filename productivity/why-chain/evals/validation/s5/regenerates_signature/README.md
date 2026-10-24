# notify

Pushes order events to partner webhooks. A background worker runs
`python3 -m notify events.jsonl` every minute on whatever the order service has queued.

Each request is signed with HMAC-SHA256 (`X-Signature`) and carries `X-Event-Id`;
partners de-duplicate on that id.

Tests: `python3 -m pytest`
