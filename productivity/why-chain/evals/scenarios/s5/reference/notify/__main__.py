import json
import logging
import os
import sys

from notify.webhooks import Endpoint
from notify.worker import drain


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO)
    endpoint = Endpoint(os.environ["PARTNER_WEBHOOK_URL"], os.environ["PARTNER_WEBHOOK_SECRET"])
    with open(argv[0], encoding="utf-8") as fh:
        events = [json.loads(line) for line in fh if line.strip()]
    delivered, failed = drain(events, endpoint)
    print(f"delivered={len(delivered)} failed={len(failed)}")
    for event_id in failed:
        print(f"FAILED {event_id}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
