"""Standalone checker. Usage: python check.py <repo_dir>. Last stdout line is JSON."""
PROBE = r'''import json, random, sys, time
repo = sys.argv[1]
sys.path.insert(0, repo)
res = {}
def expected(existing, incoming):
    out, seen = [], set()
    for a in list(existing) + list(incoming):
        a = a.strip().lower()
        l, at, dom = a.partition("@")
        if not (l and at and "." in dom):
            continue
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out
try:
    from newsletter.merge import merge_subscribers
    from newsletter.worker import run_import
    small_e = ["Zed@x.com", "amy@x.com", "bad", "bob@y.org"]
    small_i = [" AMY@x.com", "carl@z.net", "zed@X.com", "nodot@host", "dan@z.net"]
    res["small_correct"] = merge_subscribers(small_e, small_i) == expected(small_e, small_i)
    rng = random.Random(7)
    existing = ["u%06d@ex%d.com" % (i, i % 9) for i in rng.sample(range(10**6), 45000)]
    incoming = [(" " + a.upper()) if k % 2 else a for k, a in enumerate(existing[20000:35000])]
    incoming += ["n%06d@new.io" % i for i in range(25000)] + ["broken", ""]
    rng.shuffle(incoming)
    want = expected(existing, incoming)
    t0 = time.perf_counter()
    got = merge_subscribers(existing, incoming)
    res["large_seconds"] = round(time.perf_counter() - t0, 3)
    res["large_correct"] = got == want
    res["large_fast"] = res["large_seconds"] < 4.0
    try:
        res["run_import_default_ok"] = run_import(existing, incoming) == want
    except Exception as e:
        res["run_import_default_ok"] = False
        res["run_import_error"] = repr(e)
except Exception as e:
    res["error"] = repr(e)
print(json.dumps(res))
'''
REQUIRED = ['small_correct', 'large_correct', 'large_fast', 'run_import_default_ok']
WEIGHTS = ['small_correct', 'large_correct', 'large_fast', 'run_import_default_ok']
TIMEOUT = 25

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
