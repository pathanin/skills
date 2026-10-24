# billing

Small invoicing helpers used by the back office.

Export invoices for finance:

    python3 -m billing.export data/invoices.sample.json out.csv
    python3 -m billing.export data/invoices.sample.json out.csv --status paid

Run the tests with `python3 -m pytest`.
