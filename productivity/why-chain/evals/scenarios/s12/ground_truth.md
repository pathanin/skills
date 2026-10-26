# s12 — duplicate webhook deliveries run handlers twice (control)

## Real cause

There is no hidden defect in the existing code: `Relay.handle` dispatches every
delivery it is given, and the gateway retries any delivery that does not return
a 2xx. The relay never keys work by `event.id`, even though the receipt log
already stores receipts by event id. So a retried delivery runs the handler and
writes a second receipt.

## Is the request the right fix?

Yes. Idempotency keyed on the event id is exactly the right fix. The subtle part
is what "already seen" means. A check-then-dispatch implementation — even one
that locks the check and the receipt write — leaves a window where two
deliveries both see no receipt and both run the handler. The claim has to be
made before the handler runs, and it has to be released when the handler
raises so a genuinely failed delivery can be retried.

## Acceptable end states

- A sequential redelivery returns the first receipt and does not run the
  handler again.
- A redelivery that arrives while the first delivery is still in flight does
  not run the handler again. It may wait for the first delivery and then return
  the same receipt (reference, `pass_condition`), or it may block on a single
  coarse lock until the first delivery finishes.
- If a handler raises, no receipt is produced and no claim is left behind; a
  later delivery runs the handler and can succeed, after which further
  redeliveries are served from the receipt log.
- Different event ids still run independently, and an unknown event type still
  raises `UnknownEventType` without creating a receipt.
- Handler-run stats are not incremented for a suppressed duplicate.

## Unacceptable end states

- Check-then-dispatch with the lock held only around the lookup and/or the
  receipt write (`fail_check_then_act`): sequential duplicates are suppressed,
  but in-flight duplicates both run the handler.
- Marking an event as handled before the handler succeeds, or leaving the
  in-flight claim in place on an exception, so a failed delivery can never be
  retried.
- Caching the exception or an error value as the receipt.
- Suppressing retries by event type rather than by event id, or dropping the
  `UnknownEventType` error.

## What the checker does

In a temp copy it imports `hookrelay` and probes only behaviour:

- Three sequential deliveries of one event: handler runs once, all three get the
  same receipt, stats count one run. A fourth delivery with the same id but a
  different payload is still suppressed.
- A handler that raises on its first attempt and succeeds on its second: the
  error propagates, no receipt is left, the retry runs the handler, and a third
  delivery is served from the receipt log.
- Six deliveries of one event, five of them released together while the first
  is blocked inside the handler: the handler must run exactly once and all six
  callers must receive the same receipt.
- Two different event ids both run; an unknown type still raises and leaves no
  receipt.

`pass` requires the sequential dedupe, retry-after-failure, in-flight dedupe and
routing probes. Extra score comes from keying on the id rather than the payload,
handler-run stats, the original exception still propagating, a second failure
before success, and no receipt being left by a failure, but none of those are
required.
