# sales-reports

Reports built from the online-order export (`orders.csv`, exported hourly from the
order service).

    python3 -m sales.report data/orders.sample.csv     # daily totals
    python3 -m pytest
