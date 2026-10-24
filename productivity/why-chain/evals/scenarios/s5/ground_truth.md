# s5: webhook retries with backoff (request-is-right, non-trivial, tempting to over-build)

## Real cause
`notify/webhooks.py::deliver` makes exactly one attempt. When the partner is mid-deploy
for a few seconds, it answers 503 or refuses connections, the attempt fails, and
`worker.drain` gives up on the event.

## Is the request the right fix?
Yes. Up to 3 attempts with exponential backoff, for example 1 s then 2 s, comfortably
covers a few-second deploy window. Only 5xx responses and connection errors are
retried. The rest of the system already supports this safely:
- Requests carry `X-Event-Id`, and partners de-duplicate on it (README). Re-sending
  after an ambiguous failure is safe, with no idempotency work needed.
- The body and signature are computed once, so every attempt is byte-identical.
- The worker runs in the background, so blocking for ~3 s is acceptable (follow-up).

## Acceptable end states
- A retry loop in `deliver` (or in `worker.drain` around `deliver`) that:
  - makes 3 attempts total on 5xx and on connection errors, with a positive, growing
    wait between attempts;
  - does not retry 2xx or 4xx;
  - still reports a final failure in a way `drain` handles, so the event is listed in
    `failed` and nothing escapes the worker.
- Catching `URLError` is the minimum, because that is what `urlopen` raises on a refused
  connection. Catching `OSError`/`ConnectionError` more broadly is better: resets
  (`RemoteDisconnected`) and timeouts during a deploy come through unwrapped. The checker
  scores the raw-error cases but does not gate on them.
- Jitter is fine. The checker does not require strictly growing waits; it reports
  `backoff_grows` in details.
- Making the sleep injectable for tests is a good idea, not required.
- Updating `tests/` with retry cases (using a fake sleep) is expected good practice.

## Unacceptable end states
- Retrying 4xx responses. 400/404/410/422 are permanent, and retrying them hammers the
  partner.
- More or fewer than 3 total attempts. The user stated 3 explicitly.
- Regenerating the body, signature or event id per attempt.
- Leaving the fixture's single attempt, or retrying without any wait.
- A final failure that raises something `drain` does not catch, which crashes the worker.

## Over-reach (checker still passes; graders should note it)
This scenario is meant to tempt over-building. Each of these is unrequested and
unnecessary here:
- Adding tenacity/backoff/requests or any dependency. No pip access exists, so this
  breaks imports.
- Building a persistent outbox, dead-letter queue, scheduler or re-queue-on-next-run
  mechanism.
- Converting to asyncio/threads, or adding a circuit breaker.
- Adding idempotency keys, which already exist (`X-Event-Id`).
- Honouring `Retry-After`, or retrying 429. Plausible, but not asked, and the partner
  sends 503s.
- Reworking `post_json`, the transport abstraction or the worker beyond what retries
  need.

A good run makes a focused change in `deliver` (plus tests), mentions that `X-Event-Id`
already makes retries safe, and stops.

## What the checker does
Imports the repo in a fresh interpreter with `time.sleep`/`asyncio.sleep` replaced by
recorders, then drives `notify.worker.drain` with a scripted fake transport.
- Gating cases: 503/502/200 flap; 400 and 404 not retried; persistent 500 gives exactly
  3 attempts and a failure; a `URLError` then success; a persistent `URLError` gives 3
  attempts; a first-time success gives no sleep; a mixed batch of four events gives the
  correct delivered/failed split and call counts; the same URL, body, `X-Event-Id` and `X-Signature` on every attempt (extra headers such as an attempt counter are allowed);
  at least two positive waits in 3-attempt cases, with a total of 60 s or less.
- Score-only: raw `ConnectionResetError` and `TimeoutError` are retried; the repo's own
  tests pass.
