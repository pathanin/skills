def fetch_all(api, page_size=100):
    """Every invoice from the billing service, in id order."""
    invoices = []
    cursor = None
    while True:
        page = api.list_invoices(starting_at=cursor, limit=page_size)
        invoices.extend(page)
        if len(page) < page_size:
            return invoices
        # starting_at is inclusive, so resume just past the last id we have.
        cursor = page[-1].id + 1
