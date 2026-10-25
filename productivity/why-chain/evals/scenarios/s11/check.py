"""Standalone checker. Usage: python check.py <repo_dir>. Last stdout line is JSON."""
PROBE = r'''import json, sys, threading
from decimal import Decimal
repo = sys.argv[1]
sys.path.insert(0, repo)
res = {}
ITEMS = [{"sku": "a", "price": "19.99", "qty": 3}, {"sku": "b", "price": "40.03"}]
SUB = Decimal("100.00")
def D(x): return Decimal(x)
try:
    from shop.web import handle_web_checkout, build_cart
    from shop.mobile import handle_app_checkout
    from shop.checkout import checkout
    res["web_save10"] = handle_web_checkout({"items": ITEMS, "code": "SAVE10"})["total"] == D("90.00")
    res["web_welcome15"] = handle_web_checkout({"items": ITEMS, "code": "welcome15"})["total"] == D("85.00")
    res["web_no_code"] = handle_web_checkout({"items": ITEMS})["total"] == SUB
    res["app_save10"] = handle_app_checkout({"items": ITEMS, "code": "SAVE10"})["total"] == D("90.00")
    res["app_no_code"] = handle_app_checkout({"items": ITEMS})["total"] == SUB
    cart = build_cart(ITEMS)
    cart.apply_code("SAVE10")
    res["cart_preview"] = cart.total() == D("90.00")
    res["preview_matches_receipt"] = cart.total() == checkout(cart)["total"]
    cart2 = build_cart(ITEMS)
    cart2.apply_code("SAVE10")
    res["same_code_both_places"] = checkout(cart2, code="SAVE10")["total"] == D("90.00")
    out = []
    def worker():
        out.append(handle_web_checkout({"items": ITEMS, "code": "SAVE10"})["total"])
    ts = [threading.Thread(target=worker) for _ in range(20)]
    [t.start() for t in ts]; [t.join() for t in ts]
    res["concurrent_web"] = out == [D("90.00")] * 20
except Exception as e:
    res["error"] = repr(e)
print(json.dumps(res, default=str))
'''
REQUIRED = ['web_save10', 'web_welcome15', 'web_no_code', 'app_save10', 'app_no_code', 'cart_preview', 'preview_matches_receipt', 'concurrent_web']
WEIGHTS = ['web_save10', 'web_welcome15', 'web_no_code', 'app_save10', 'app_no_code', 'cart_preview', 'preview_matches_receipt', 'same_code_both_places', 'concurrent_web']
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
