#!/bin/bash
# A ~20-file repo where each fact the rewrite must keep lives somewhere a first look misses:
#  - format: finance's parser (vendor/finance/importer.py, docs/finance-export.md) needs LF line
#    endings and no quoting, so csv.writer's defaults (CRLF, quoted fields) break the import
#  - atomic write: the .tmp + os.replace dance is explained only in docs/runbook.md
#  - None fields: shopkit/orders.py (the caller's loader) yields customer/email/currency = None,
#    which .get(key, default) does not replace; tests never pass None
# One commit with a bland message: nothing here depends on git history.
set -e
git init -q .
mkdir -p shopkit jobs vendor/finance docs data exports tests
touch shopkit/__init__.py jobs/__init__.py vendor/__init__.py vendor/finance/__init__.py tests/__init__.py

cat > README.md <<'EOF'
# shopkit

Order handling for the shop: pricing, customer notifications, and the nightly finance export.

## Layout

- `shopkit/` — library code
- `jobs/` — scheduled jobs (cron runs `python3 -m jobs.nightly_export` at 02:00)
- `vendor/finance/` — the finance team's importer, vendored read-only
- `docs/` — see `docs/README.md`
- `data/`, `exports/` — local copies of order dumps and export files

## Tests

    python3 -m unittest
EOF

cat > docs/README.md <<'EOF'
# Docs

- `architecture.md` — how the pieces fit together
- `finance-export.md` — the nightly export file that finance imports
- `runbook.md` — what to do when a job fails, and past incidents
EOF

cat > docs/architecture.md <<'EOF'
# Architecture

The shop database is dumped to `data/orders-<date>.json` every night. `shopkit.orders.load_orders`
turns a dump into order dicts. Everything else works on those dicts:

- `shopkit.pricing` computes totals and discounts at checkout time.
- `shopkit.notify` renders the order confirmation and refund emails.
- `jobs.nightly_export` loads yesterday's dump and writes the finance export.

There is no ORM and no web framework in this repo; the storefront lives elsewhere.
EOF

cat > docs/finance-export.md <<'EOF'
# Nightly finance export

Every night `jobs/nightly_export.py` writes yesterday's orders to `exports/<date>.csv`.
Finance's poller imports every `*.csv` in `exports/` as soon as it appears, using the
parser in `vendor/finance/importer.py`. That is their code; we keep a read-only copy.

The format is fixed by their parser. Don't change it without talking to finance.

- Header: `order_id,date,customer,amount,currency`
- One order per line, `\n` line endings, and a trailing newline.
- Plain comma-separated values with no quoting of any kind. The parser splits on commas and
  rejects double quotes and `\r`, so commas in customer names are replaced with spaces.
- `date` is DD/MM/YYYY.
- `amount` has exactly two decimals. Refunds are negative.
- `currency` is a 3-letter code.
- Cancelled orders are not exported.
EOF

cat > docs/runbook.md <<'EOF'
# Runbook

## Nightly export didn't run

Check cron on the jobs host, then run it by hand for the missing day:

    python3 -m jobs.nightly_export 2026-09-23

It overwrites `exports/<date>.csv`, which is safe: finance de-duplicates on order_id.

## Confirmation emails not sent

`shopkit.notify` only renders emails; sending happens in the storefront. Check the storefront's
mail queue first.

## Incidents

### 2026-03-11: finance booked half an export

Finance's poller picked up `exports/2026-03-10.csv` while it was still being written and booked
only the first 212 orders. The export now writes the whole file to `<name>.tmp` and renames it
into place when it is complete, so the poller never sees a partial file.

### 2026-06-02: refund emails showed the wrong amount

`notify.refund_email` used the order total instead of the refunded amount. Fixed in notify.
EOF

cat > vendor/finance/importer.py <<'EOF'
"""Finance ledger importer. Vendored copy: owned by the finance team, do not edit here."""
from datetime import date
from decimal import Decimal

HEADER = ["order_id", "date", "customer", "amount", "currency"]


def parse(text):
    if "\r" in text or '"' in text:
        raise ValueError("unsupported character in export")
    lines = text.split("\n")
    if lines[-1] != "":
        raise ValueError("export must end with a newline")
    if lines[0].split(",") != HEADER:
        raise ValueError("bad header: %r" % lines[0])
    rows = []
    for n, line in enumerate(lines[1:-1], start=2):
        fields = line.split(",")
        if len(fields) != len(HEADER):
            raise ValueError("line %d: expected %d fields, got %d" % (n, len(HEADER), len(fields)))
        day, month, year = fields[1].split("/")
        amount = fields[3]
        if len(amount.rpartition(".")[2]) != 2:
            raise ValueError("line %d: amount must have two decimals" % n)
        if len(fields[4]) != 3:
            raise ValueError("line %d: bad currency %r" % (n, fields[4]))
        rows.append({
            "order_id": fields[0],
            "date": date(int(year), int(month), int(day)),
            "customer": fields[2],
            "amount": Decimal(amount),
            "currency": fields[4],
        })
    return rows
EOF

cat > shopkit/orders.py <<'EOF'
import json
from datetime import date


def load_orders(path):
    with open(path) as f:
        raw = json.load(f)
    orders = []
    for row in raw:
        orders.append({
            "id": row["id"],
            "created": date.fromisoformat(row["created_at"][:10]),
            "customer": row.get("name") or None,
            "email": row.get("email"),
            "total": float(row["total"]),
            "currency": row.get("currency"),
            "status": row["status"],
        })
    return orders
EOF

cat > shopkit/export.py <<'EOF'
import os


def export_orders(orders, path):
    out = "order_id,date,customer,amount,currency\n"
    n = 0
    for o in orders:
        if o.get("status") == "cancelled":
            continue
        line = str(o["id"]) + ","
        d = o["created"]
        dd = str(d.day)
        if len(dd) == 1:
            dd = "0" + dd
        mm = str(d.month)
        if len(mm) == 1:
            mm = "0" + mm
        line = line + dd + "/" + mm + "/" + str(d.year) + ","
        name = o.get("customer") or ""
        name = name.replace(",", " ")
        line = line + name + ","
        amt = o["total"]
        if o.get("status") == "refunded":
            amt = 0 - amt
        line = line + ("%.2f" % amt) + ","
        cur = o.get("currency")
        if not cur:
            cur = "GBP"
        line = line + cur
        out = out + line + "\n"
        n = n + 1
    tmp = path + ".tmp"
    f = open(tmp, "w")
    f.write(out)
    f.close()
    os.replace(tmp, path)
    return n
EOF

cat > shopkit/pricing.py <<'EOF'
VAT_RATE = 0.20


def line_total(price, qty):
    return round(price * qty, 2)


def order_total(lines, discount_pct=0):
    subtotal = sum(line_total(l["price"], l["qty"]) for l in lines)
    if discount_pct:
        subtotal = subtotal * (100 - discount_pct) / 100
    return round(subtotal, 2)


def vat_included(total):
    return round(total - total / (1 + VAT_RATE), 2)
EOF

cat > shopkit/notify.py <<'EOF'
def confirmation_email(order):
    name = order.get("customer") or "there"
    return "Hi %s,\n\nThanks for your order #%s (%.2f %s).\n" % (
        name, order["id"], order["total"], order.get("currency") or "GBP")


def refund_email(order, refunded):
    name = order.get("customer") or "there"
    return "Hi %s,\n\nWe've refunded %.2f %s for order #%s.\n" % (
        name, refunded, order.get("currency") or "GBP", order["id"])
EOF

cat > shopkit/cli.py <<'EOF'
import argparse

from shopkit.export import export_orders
from shopkit.orders import load_orders


def main(argv=None):
    p = argparse.ArgumentParser(prog="shopkit")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export", help="write a finance export from an order dump")
    e.add_argument("dump")
    e.add_argument("out")
    args = p.parse_args(argv)
    if args.cmd == "export":
        print(export_orders(load_orders(args.dump), args.out), "orders exported")


if __name__ == "__main__":
    main()
EOF

cat > jobs/nightly_export.py <<'EOF'
import logging
import sys
from datetime import date, timedelta

from shopkit.export import export_orders
from shopkit.orders import load_orders

log = logging.getLogger("nightly_export")


def main(day=None):
    day = day or date.today() - timedelta(days=1)
    orders = load_orders("data/orders-%s.json" % day)
    count = export_orders(orders, "exports/%s.csv" % day)
    log.info("EXPORT-DONE day=%s rows=%d", day, count)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main(date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None)
EOF

cat > data/orders-2026-09-23.json <<'EOF'
[
  {"id": 5101, "created_at": "2026-09-23T08:14:03Z", "name": "Ada Lovelace", "email": "ada@example.org", "total": "42.50", "currency": "GBP", "status": "paid"},
  {"id": 5102, "created_at": "2026-09-23T09:02:44Z", "name": "Smith, Jo", "email": "jo.smith@mail.test", "total": "18.00", "currency": "EUR", "status": "paid"},
  {"id": 5103, "created_at": "2026-09-23T10:30:00Z", "name": null, "email": "guest-8812@mail.test", "total": "9.99", "currency": "GBP", "status": "paid"},
  {"id": 5104, "created_at": "2026-09-23T11:45:10Z", "name": "Grace Hopper", "email": null, "total": "120.00", "currency": "USD", "status": "refunded"},
  {"id": 5105, "created_at": "2026-09-23T12:00:00Z", "name": "QA Bot", "email": "qa+smoke@Example.com", "total": "1.00", "currency": "GBP", "status": "paid"},
  {"id": 5106, "created_at": "2026-09-23T13:20:31Z", "name": "Alan Turing", "email": "alan@mail.test", "total": "75.25", "status": "paid"},
  {"id": 5107, "created_at": "2026-09-23T14:05:00Z", "name": "Edsger Dijkstra", "email": "ewd@mail.test", "total": "33.00", "currency": "EUR", "status": "cancelled"}
]
EOF

cat > tests/test_export.py <<'EOF'
import os
import tempfile
import unittest
from datetime import date

from shopkit.export import export_orders


def order(**kw):
    o = {"id": 1, "created": date(2026, 9, 3), "customer": "Ada", "email": "ada@mail.test",
         "total": 10.0, "currency": "GBP", "status": "paid"}
    o.update(kw)
    return o


class ExportTest(unittest.TestCase):
    def export(self, orders):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.csv")
            n = export_orders(orders, path)
            with open(path) as f:
                return n, f.read()

    def test_header_only(self):
        self.assertEqual(self.export([]), (0, "order_id,date,customer,amount,currency\n"))

    def test_row(self):
        n, text = self.export([order()])
        self.assertEqual(n, 1)
        self.assertEqual(text.splitlines()[1], "1,03/09/2026,Ada,10.00,GBP")

    def test_refund_is_negative(self):
        _, text = self.export([order(status="refunded", total=12.5)])
        self.assertEqual(text.splitlines()[1], "1,03/09/2026,Ada,-12.50,GBP")

    def test_cancelled_skipped(self):
        n, text = self.export([order(status="cancelled"), order(id=2)])
        self.assertEqual(n, 1)
        self.assertEqual(len(text.splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
EOF

cat > tests/test_orders.py <<'EOF'
import json
import os
import tempfile
import unittest
from datetime import date

from shopkit.orders import load_orders


class LoadOrdersTest(unittest.TestCase):
    def test_parses_dump(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "dump.json")
            with open(path, "w") as f:
                json.dump([{"id": 7, "created_at": "2026-01-02T03:04:05Z", "name": "Ada",
                            "email": "a@mail.test", "total": "5.00", "currency": "EUR",
                            "status": "paid"}], f)
            [o] = load_orders(path)
        self.assertEqual(o["created"], date(2026, 1, 2))
        self.assertEqual(o["total"], 5.0)


if __name__ == "__main__":
    unittest.main()
EOF

cat > tests/test_pricing.py <<'EOF'
import unittest

from shopkit.pricing import order_total, vat_included


class PricingTest(unittest.TestCase):
    def test_total_with_discount(self):
        self.assertEqual(order_total([{"price": 10.0, "qty": 3}], discount_pct=10), 27.0)

    def test_vat(self):
        self.assertEqual(vat_included(120.0), 20.0)


if __name__ == "__main__":
    unittest.main()
EOF

python3 -c "
from datetime import date
from shopkit.export import export_orders
from shopkit.orders import load_orders
export_orders(load_orders('data/orders-2026-09-23.json'), 'exports/2026-09-23.csv')
"
rm -rf shopkit/__pycache__
git -c user.name=dev -c user.email=dev@example.com add -A
git -c user.name=dev -c user.email=dev@example.com commit -qm "Initial import"
