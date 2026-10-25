import pytest

from invoices.api import InvoiceAPI
from invoices.fetch import fetch_all
from invoices.models import Invoice


@pytest.mark.parametrize("page_size", [2, 7, 100])
def test_no_duplicates_across_pages(page_size):
    invs = [Invoice(10 + 3 * i, "c", "2026-09", 1) for i in range(250)]
    got = fetch_all(InvoiceAPI(invs), page_size=page_size)
    assert [i.id for i in got] == [i.id for i in invs]
