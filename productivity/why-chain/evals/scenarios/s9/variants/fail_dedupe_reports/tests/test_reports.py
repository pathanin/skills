from invoices.api import InvoiceAPI
from invoices.fetch import fetch_all
from invoices.models import Invoice
from invoices.reports import customer_totals, revenue_report

INVOICES = [
    Invoice(1, "acme", "2026-09", 500),
    Invoice(2, "acme", "2026-08", 700),
    Invoice(5, "globex", "2026-09", 300),
]


def test_revenue_report():
    r = revenue_report(fetch_all(InvoiceAPI(INVOICES)), "2026-09")
    assert r["count"] == 2 and r["total_cents"] == 800


def test_customer_totals():
    assert customer_totals(fetch_all(InvoiceAPI(INVOICES))) == {"acme": 1200, "globex": 300}
