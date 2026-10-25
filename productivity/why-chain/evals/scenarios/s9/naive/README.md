# invoices

Pulls invoices from the billing service and produces finance reports.

- `invoices.api.InvoiceAPI` — client for the billing service's `/invoices`
  endpoint (an in-process stand-in is used in tests and local runs).
- `invoices.fetch.fetch_all` — pages through every invoice.
- `invoices.reports` — `revenue_report` (monthly totals for finance) and
  `customer_totals` (lifetime spend per customer, used by account managers).

    python -m invoices.reports 2026-09
