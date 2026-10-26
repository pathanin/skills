# hookrelay

Incoming webhook relay used by the platform team.

The gateway POSTs every delivery to `hookrelay.relay.Relay.handle`. The relay
looks up a handler by event type, runs it, and stores a receipt in the receipt
log. The receipt log is what the customer-facing `/receipts/<event id>` endpoint
serves.

The sender assigns an `id` to each event and may deliver the same id more than
once.

- `hookrelay.events` parses and validates delivery bodies.
- `hookrelay.handlers` maps event types to handler functions.
- `hookrelay.receipts` keeps the receipts served by the receipts endpoint.
- `hookrelay.stats` counts handler runs per event type.
- `hookrelay.relay.Relay` ties the pieces together.

The gateway retries any delivery that does not return a 2xx response, and
handlers raise when a downstream service is unavailable.
