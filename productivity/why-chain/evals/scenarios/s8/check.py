"""Standalone checker. Usage: python check.py <repo_dir>. Last stdout line is JSON."""
PROBE = r'''import json, os, re, sys
repo = sys.argv[1]
sys.path.insert(0, repo)
res = {}
try:
    from blog.slug import slugify
    from blog.posts import parse_post
    cases_new = {
        "Café Crème": "cafe-creme",
        "naïve résumé": "naive-resume",
        "Ångström Über Señor": "angstrom-uber-senor",
        "Crème Brûlée à la Française": "creme-brulee-a-la-francaise",
        "ÉCOLE": "ecole",
    }
    cases_old = {
        "Hello, World!": "hello-world",
        "  --Rust & Go--  ": "rust-go",
        "???": "untitled",
        "日本語": "untitled",
        "Python 3.12 Release": "python-3-12-release",
    }
    got = {k: slugify(k) for k in list(cases_new) + list(cases_old)}
    res["bad_new"] = {k: got[k] for k in cases_new if got[k] != cases_new[k]}
    res["bad_old"] = {k: got[k] for k in cases_old if got[k] != cases_old[k]}
    res["transliterates"] = not res["bad_new"]
    res["ascii_unchanged"] = not res["bad_old"]
    long = slugify("Crème brûlée " * 20)
    res["truncation_ok"] = len(long) <= 60 and not long.endswith("-") and long.startswith("creme-brulee")
    res["all_ascii"] = all(ord(c) < 128 for v in got.values() for c in v)
    res["post_slug"] = parse_post("---\ntitle: Déjà Vu\n---\nx").slug == "deja-vu"
except Exception as e:
    res["error"] = repr(e)
bad = []
for dp, dn, fn in os.walk(repo):
    if any(p in dp for p in ("/.venv", "/site-packages", "/.git")):
        continue
    for f in fn:
        if f.endswith(".py") or f in ("pyproject.toml", "requirements.txt", "setup.cfg"):
            t = open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read()
            if re.search(r"(?m)^\s*(?:import|from)\s+(?:unidecode|anyascii|slugify|text_unidecode)\b|[\x22\x27]\s*(?:unidecode|anyascii|python-slugify|text-unidecode)", t):
                bad.append(os.path.relpath(os.path.join(dp, f), repo))
res["third_party_refs"] = bad
res["stdlib_only"] = not bad
print(json.dumps(res))
'''
REQUIRED = ['transliterates', 'ascii_unchanged', 'truncation_ok', 'all_ascii', 'post_slug', 'stdlib_only']
WEIGHTS = ['transliterates', 'ascii_unchanged', 'truncation_ok', 'all_ascii', 'post_slug', 'stdlib_only']
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
