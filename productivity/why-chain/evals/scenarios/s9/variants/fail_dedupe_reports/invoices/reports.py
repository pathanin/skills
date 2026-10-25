import sys
from collections import defaultdict

from .fetch import fetch_all


def revenue_report(invoices, month):
    unique = {inv.id: inv for inv in invoices}
    rows = [inv for inv in unique.values() if inv.month == month]
    return {
        "month": month,
        "count": len(rows),
        "total_cents": sum(inv.amount_cents for inv in rows),
        "invoice_ids": [inv.id for inv in rows],
    }


def customer_totals(invoices):
    totals = defaultdict(int)
    for inv in {inv.id: inv for inv in invoices}.values():
        totals[inv.customer] += inv.amount_cents
    return dict(totals)


def _demo_api():
    from .api import InvoiceAPI
    from .models import Invoice
    return InvoiceAPI([
        Invoice(1000 + 3 * i, f"cust{i % 17}", "2026-09" if i % 2 else "2026-08", 1000 + 7 * i)
        for i in range(420)
    ])


if __name__ == "__main__":
    report = revenue_report(fetch_all(_demo_api()), sys.argv[1])
    print(f"{report['month']}: {report['count']} invoices, {report['total_cents'] / 100:.2f}")
