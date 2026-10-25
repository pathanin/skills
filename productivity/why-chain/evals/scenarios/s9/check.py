"""Standalone checker. Usage: python check.py <repo_dir>. Last stdout line is JSON."""
PROBE = r'''import json, sys
from collections import defaultdict
repo = sys.argv[1]
sys.path.insert(0, repo)
res = {}
try:
    from invoices.api import InvoiceAPI
    from invoices.fetch import fetch_all
    from invoices.models import Invoice
    from invoices.reports import revenue_report, customer_totals
    invs = [Invoice(500 + 4 * i, "c%d" % (i % 11), "2026-09" if i % 3 else "2026-08", 100 + i) for i in range(350)]
    want_ids = [i.id for i in invs]
    fetch_ok = True
    for ps in (None, 50, 7, 3):
        got = fetch_all(InvoiceAPI(invs)) if ps is None else fetch_all(InvoiceAPI(invs), page_size=ps)
        if [i.id for i in got] != want_ids:
            fetch_ok = False
            res["fetch_bad_page_size_%s" % ps] = len(got)
    res["fetch_all_exact"] = fetch_ok
    data = fetch_all(InvoiceAPI(invs))
    sep = [i for i in invs if i.month == "2026-09"]
    r = revenue_report(data, "2026-09")
    res["revenue_ok"] = r["count"] == len(sep) and r["total_cents"] == sum(i.amount_cents for i in sep)
    want = defaultdict(int)
    for i in invs:
        want[i.customer] += i.amount_cents
    res["customer_totals_ok"] = customer_totals(data) == dict(want)
    res["small_ok"] = [i.id for i in fetch_all(InvoiceAPI(invs[:5]))] == want_ids[:5]
except Exception as e:
    res["error"] = repr(e)
print(json.dumps(res))
'''
REQUIRED = ['fetch_all_exact', 'revenue_ok', 'customer_totals_ok', 'small_ok']
WEIGHTS = ['fetch_all_exact', 'revenue_ok', 'customer_totals_ok', 'small_ok']
TIMEOUT = 60

import json, os, shutil, subprocess, sys, tempfile

def run_probe(repo, timeout):
    tmp = tempfile.mkdtemp(prefix="chk_")
    dst = os.path.join(tmp, "repo")
    shutil.copytree(repo, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".venv"))
    probe = os.path.join(tmp, "probe.py")
    with open(probe, "w") as f:
        f.write(PROBE)
    try:
        r = subprocess.run([sys.executable, probe, dst], capture_output=True, text=True, timeout=timeout, cwd=tmp)
    except subprocess.TimeoutExpired:
        return None, "probe timed out after %ss" % timeout
    lines = [l for l in r.stdout.strip().splitlines() if l.strip()]
    try:
        return json.loads(lines[-1]), None
    except Exception:
        return None, "probe crashed: " + (r.stderr[-1500:] or r.stdout[-500:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def main():
    if len(sys.argv) != 2:
        print("usage: python check.py <repo_dir>")
        sys.exit(2)
    res, err = run_probe(os.path.abspath(sys.argv[1]), TIMEOUT)
    if res is None:
        print(json.dumps({"pass": False, "score": 0.0, "details": {"error": err}}))
        return
    ok = all(res.get(k) is True for k in REQUIRED)
    score = sum(1 for k in WEIGHTS if res.get(k) is True) / len(WEIGHTS)
    if not ok:
        score = min(score, 0.6)
    print(json.dumps({"pass": ok, "score": round(score, 3), "details": res}))

if __name__ == "__main__":
    main()
