"""Export invoices to CSV for the finance team."""
import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, TextIO

from billing.models import Invoice

COLUMNS = ["invoice_id", "customer", "email", "amount", "issued_on"]


def load_invoices(path: Path) -> list[Invoice]:
    with open(path, encoding="utf-8") as fh:
        return [Invoice.from_dict(item) for item in json.load(fh)]


def invoice_row(inv: Invoice) -> list[str]:
    return [inv.id, inv.customer, inv.email, f"{inv.amount:.2f}", inv.issued_on.isoformat()]


def _cell(value: str) -> str:
    return f'"{value}"' if "," in value else value


def export_invoices(invoices: Iterable[Invoice], out: TextIO) -> int:
    out.write(",".join(COLUMNS) + "\n")
    count = 0
    for inv in invoices:
        out.write(",".join(_cell(v) for v in invoice_row(inv)) + "\n")
        count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("dest", type=Path)
    parser.add_argument("--status", help="only export invoices with this status")
    args = parser.parse_args(argv)

    invoices = load_invoices(args.source)
    if args.status:
        invoices = [inv for inv in invoices if inv.status == args.status]
    invoices.sort(key=lambda inv: (inv.issued_on, inv.id))

    with open(args.dest, "w", encoding="utf-8") as out:
        count = export_invoices(invoices, out)
    print(f"wrote {count} invoices to {args.dest}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
