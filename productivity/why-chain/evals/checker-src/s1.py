

# ---------------------------------------------------------------- s1 specific
import csv

INVOICES = [
    {"id": "INV-2001", "customer": "Northwind Traders", "email": "ap@northwind.example", "amount": "1200", "issued_on": "2026-09-01", "status": "paid"},
    {"id": "INV-2002", "customer": "Smith, Jones & Co", "email": "AP@SmithJones.example", "amount": "349.5", "issued_on": "2026-09-02", "status": "paid"},
    {"id": "INV-2003", "customer": "\"Quoted\" Name Inc", "email": "hi@quoted.example", "amount": "88.20", "issued_on": "2026-09-03", "status": "paid"},
    {"id": "INV-2004", "customer": "Zoë's Café, Ltd.", "email": "zoe@cafe.example", "amount": "15.05", "issued_on": "2026-09-04", "status": "paid"},
    {"id": "INV-2005", "customer": "Garcia, \"Big G\", Hauling", "email": "g@hauling.example", "amount": "7", "issued_on": "2026-09-05", "status": "open"},
    {"id": "INV-2006", "customer": "Plain Name LLC", "email": "plain@example.com", "amount": "0.99", "issued_on": "2026-09-06", "status": "paid"},
]
HEADER = ["invoice_id", "customer", "email", "amount", "issued_on"]


def expected_rows(status=None):
    rows = []
    for inv in INVOICES:
        if status and inv["status"] != status:
            continue
        rows.append([inv["id"], inv["customer"].strip(), inv["email"].strip().lower(),
                     f"{float(inv['amount']):.2f}", inv["issued_on"]])
    return rows


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.reader(fh))


def check(repo: Path):
    details = {}
    tmp = Path(tempfile.mkdtemp(prefix="chk_s1_"))
    try:
        work = copy_repo(repo, tmp)
        src = tmp / "invoices.json"
        src.write_text(json.dumps(INVOICES, ensure_ascii=False), encoding="utf-8")

        for label, extra in (("all", []), ("paid", ["--status", "paid"])):
            dest = tmp / f"out_{label}.csv"
            p = run([sys.executable, "-B", "-m", "billing.export", str(src), str(dest), *extra], work)
            key = f"export_{label}_roundtrips"
            if p.returncode != 0 or not dest.exists():
                details[key] = False
                details[f"export_{label}_error"] = f"exit {p.returncode}: {p.stderr[-600:]}"
                continue
            rows = read_csv(dest)
            want = [HEADER] + expected_rows("paid" if label == "paid" else None)
            details[key] = rows == want
            if rows != want:
                details[f"export_{label}_got"] = rows[:8]

        ok_tests, tail = repo_tests(work)
        details["repo_tests_pass"] = ok_tests
        if not ok_tests:
            details["repo_tests_tail"] = tail

        gating = [details["export_all_roundtrips"], details["export_paid_roundtrips"]]
        allchecks = gating + [ok_tests]
        return all(gating), sum(allchecks) / len(allchecks), details
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    emit(check)
