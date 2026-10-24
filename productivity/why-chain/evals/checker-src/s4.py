

# ---------------------------------------------------------------- s4 specific
import csv
import io
import re
from decimal import Decimal, InvalidOperation

ORDERS = [
    ("C-01", "2026-03-06T20:15:00Z", "42.50", "paid"),
    ("C-02", "2026-03-07T03:40:00Z", "18.25", "paid"),
    ("C-03", "2026-03-07T07:30:00Z", "9.75", "paid"),
    ("C-04", "2026-03-07T17:05:00Z", "64.00", "paid"),
    ("C-05", "2026-03-08T05:10:00Z", "120.40", "paid"),
    ("C-06", "2026-03-08T10:30:00Z", "33.30", "paid"),
    ("C-07", "2026-03-08T19:00:00Z", "15.00", "refunded"),
    ("C-08", "2026-03-09T06:45:00Z", "27.80", "paid"),
    ("C-09", "2026-03-09T07:15:00Z", "11.10", "paid"),
    ("C-10", "2026-03-09T18:20:00Z", "5.55", "paid"),
    ("C-11", "2026-07-14T06:59:00Z", "54.20", "paid"),
    ("C-12", "2026-07-14T07:30:00Z", "8.40", "paid"),
    ("C-13", "2026-07-14T22:00:00Z", "19.99", "paid"),
    ("C-14", "2026-07-15T02:30:00Z", "73.10", "paid"),
    ("C-15", "2026-07-15T16:45:00Z", "12.35", "Paid"),
    ("C-16", "2026-10-31T06:30:00Z", "31.00", "paid"),
    ("C-17", "2026-11-01T07:30:00Z", "12.00", "paid"),
    ("C-18", "2026-11-01T08:30:00Z", "6.50", "paid"),
    ("C-19", "2026-11-02T07:30:00Z", "21.00", "paid"),
    ("C-20", "2026-11-02T08:30:00Z", "4.25", "paid"),
    ("C-21", "2026-11-02T09:15:00Z", "17.45", "refunded"),
]

# Store-local (America/Los_Angeles) business dates, computed with zoneinfo when the checker was written.
EXPECTED = {
    "2026-03-06": "70.50", "2026-03-07": "184.40", "2026-03-08": "61.10", "2026-03-09": "16.65",
    "2026-07-13": "54.20", "2026-07-14": "101.49", "2026-07-15": "12.35",
    "2026-10-30": "31.00", "2026-11-01": "39.50", "2026-11-02": "4.25",
}
MACHINE_TZS = ["UTC", "Asia/Tokyo", "America/New_York"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_report(text):
    out = {}
    for row in csv.reader(io.StringIO(text)):
        if not row or not DATE_RE.match(row[0].strip()):
            continue
        raw = re.sub(r"[^0-9.\-]", "", row[-1])
        try:
            out[row[0].strip()] = Decimal(raw).quantize(Decimal("0.01"))
        except InvalidOperation:
            out[row[0].strip()] = row[-1]
    return out


def check(repo: Path):
    details = {}
    tmp = Path(tempfile.mkdtemp(prefix="chk_s4_"))
    try:
        work = copy_repo(repo, tmp)
        src = tmp / "orders.csv"
        with open(src, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["order_id", "created_at", "amount", "status", "register"])
            for oid, ts, amt, status in ORDERS:
                w.writerow([oid, ts, amt, status, "web"])

        want = {k: Decimal(v) for k, v in EXPECTED.items()}
        per_tz = {}
        for tz in MACHINE_TZS:
            p = run([sys.executable, "-B", "-m", "sales.report", str(src)], work, timeout=30, env_extra={"TZ": tz})
            if p.returncode != 0:
                per_tz[tz] = False
                details[f"error_{tz}"] = p.stderr[-500:]
                continue
            got = parse_report(p.stdout)
            per_tz[tz] = got == want
            if got != want:
                details[f"wrong_days_{tz}"] = {d: [str(got.get(d)), str(want.get(d))]
                                               for d in sorted(set(got) | set(want)) if got.get(d) != want.get(d)}
        details["matches_store_local_days"] = per_tz

        total = sum(want.values())
        details["grand_total_expected"] = str(total)

        ok_tests, tail = repo_tests(work, env_extra={"TZ": "UTC"})
        details["repo_tests_pass"] = ok_tests
        if not ok_tests:
            details["repo_tests_tail"] = tail

        gating = list(per_tz.values())
        allchecks = gating + [ok_tests]
        return all(gating), sum(allchecks) / len(allchecks), details
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    emit(check)
