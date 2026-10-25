class InvoiceAPI:
    """Billing service `/invoices` endpoint.

    list_invoices(starting_at=None, limit=100) returns up to `limit` invoices
    ordered by id, beginning with the first invoice whose id is >= starting_at
    (from the start when starting_at is None).
    """

    def __init__(self, invoices):
        self._rows = sorted(invoices, key=lambda inv: inv.id)
        self.calls = 0

    def list_invoices(self, starting_at=None, limit=100):
        self.calls += 1
        rows = self._rows
        if starting_at is not None:
            rows = [inv for inv in rows if inv.id >= starting_at]
        return rows[:limit]
