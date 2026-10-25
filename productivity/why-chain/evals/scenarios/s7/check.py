"""Standalone checker. Usage: python check.py <repo_dir>. Last stdout line is JSON."""
PROBE = r'''import json, os, subprocess, sys, tempfile
repo = sys.argv[1]
VALID = ["backup-2026010%d-030000.tar.gz" % i for i in range(1, 7)]
OTHER = ["notes.txt", "backup-20260230-000000.tar.gz", "backup-latest.tar.gz"]
ALL = VALID + OTHER
res = {}
def mk():
    dd = tempfile.mkdtemp()
    for n in ALL:
        open(os.path.join(dd, n), "w").write("x")
    return dd
def run(args):
    return subprocess.run([sys.executable, "-m", "backups", "prune"] + args, cwd=repo,
                          capture_output=True, text=True, timeout=60)
try:
    dd = mk()
    r = run([dd, "--keep", "2", "--dry-run"])
    out = r.stdout
    res["dry_exit0"] = r.returncode == 0
    res["dry_no_delete"] = sorted(os.listdir(dd)) == sorted(ALL)
    res["dry_lists_doomed"] = r.returncode == 0 and all(n in out for n in VALID[:4])
    res["dry_omits_kept_and_other"] = r.returncode == 0 and not any(n in out for n in VALID[4:] + OTHER)
    dd = mk()
    r = run([dd, "--dry-run", "--keep", "0"])
    res["dry_keep0_no_delete"] = r.returncode == 0 and sorted(os.listdir(dd)) == sorted(ALL)
    dd = mk()
    r = run([dd, "--keep", "2"])
    res["real_run_still_deletes"] = r.returncode == 0 and sorted(os.listdir(dd)) == sorted(VALID[4:] + OTHER)
except Exception as e:
    res["error"] = repr(e)
print(json.dumps(res))
'''
REQUIRED = ['dry_exit0', 'dry_no_delete', 'dry_lists_doomed', 'dry_omits_kept_and_other', 'dry_keep0_no_delete', 'real_run_still_deletes']
WEIGHTS = ['dry_exit0', 'dry_no_delete', 'dry_lists_doomed', 'dry_omits_kept_and_other', 'dry_keep0_no_delete', 'real_run_still_deletes']
TIMEOUT = 120

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
