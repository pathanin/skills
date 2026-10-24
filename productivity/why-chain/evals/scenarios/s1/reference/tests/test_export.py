import io
from datetime import date
from decimal import Decimal

from billing.export import export_invoices, main
from billing.models import Invoice


def make(id_, customer="Acme", amount="10.00", status="open"):
    return Invoice(id_, customer, "ap@acme.example", Decimal(amount), date(2026, 9, 1), status)


def test_header_and_rows():
    buf = io.StringIO()
    n = export_invoices([make("INV-1"), make("INV-2", amount="5.5")], buf)
    lines = buf.getvalue().splitlines()
    assert n == 2
    assert lines[0] == "invoice_id,customer,email,amount,issued_on"
    assert lines[1] == "INV-1,Acme,ap@acme.example,10.00,2026-09-01"
    assert lines[2] == "INV-2,Acme,ap@acme.example,5.50,2026-09-01"


def test_cli_filters_by_status(tmp_path):
    src = tmp_path / "in.json"
    src.write_text(
        '[{"id": "A", "customer": "X", "email": "x@x.example", "amount": "1", "issued_on": "2026-01-02", "status": "paid"},'
        ' {"id": "B", "customer": "Y", "email": "y@y.example", "amount": "2", "issued_on": "2026-01-01", "status": "open"}]'
    )
    dest = tmp_path / "out.csv"
    assert main([str(src), str(dest), "--status", "paid"]) == 0
    rows = dest.read_text().splitlines()
    assert rows[1:] == ["A,X,x@x.example,1.00,2026-01-02"]
