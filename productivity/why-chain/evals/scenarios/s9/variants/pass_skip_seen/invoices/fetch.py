def fetch_all(api, page_size=100):
    """Every invoice from the billing service, in id order."""
    invoices = []
    cursor = None
    while True:
        page = api.list_invoices(starting_at=cursor, limit=page_size)
        new = [inv for inv in page if cursor is None or inv.id > cursor]
        invoices.extend(new)
        if len(page) < page_size or not new:
            return invoices
        cursor = page[-1].id
