"""Checker for s6. Usage: python3 check.py <path-to-final-repo>. Prints one JSON object."""
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc", ".DS_Store")
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache"}


def copy_repo(repo: Path, tmp: Path) -> Path:
    work = tmp / "repo"
    shutil.copytree(repo, work, ignore=IGNORE)
    return work


def run(cmd, cwd, timeout=60, env_extra=None, input=None):
    env = dict(os.environ)
    for key in ("PYTHONHASHSEED", "PYTHONPATH", "TZ"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, input=input)


def run_py(code, cwd, timeout=60, env_extra=None):
    """Run a snippet in a fresh interpreter with the repo on sys.path; expects JSON on the last stdout line."""
    p = run([sys.executable, "-B", "-c", code], cwd, timeout=timeout, env_extra=env_extra)
    lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
    try:
        return json.loads(lines[-1]), p
    except Exception:
        return None, p


def repo_tests(work: Path, env_extra=None, timeout=120):
    try:
        p = run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"], work, timeout=timeout, env_extra=env_extra)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    return p.returncode == 0, p.stdout[-800:]


def _files(root: Path):
    out = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if path.is_file() and not (set(rel.parts) & SKIP_PARTS) and path.suffix != ".pyc" and path.name != ".DS_Store":
            out[rel.as_posix()] = path.read_bytes()
    return out


def changed_files(repo: Path):
    """Detail only: which files differ from the original fixture."""
    fixture = HERE / "fixture"
    if not fixture.is_dir():
        return None
    a, b = _files(fixture), _files(repo)
    return {
        "added": sorted(set(b) - set(a)),
        "removed": sorted(set(a) - set(b)),
        "modified": sorted(k for k in set(a) & set(b) if a[k] != b[k]),
    }


def non_stdlib_imports(repo: Path):
    """Detail only: third-party modules imported anywhere in the repo."""
    local = {p.name for p in repo.iterdir() if p.is_dir() or p.suffix == ".py"}
    local |= {p.stem for p in repo.iterdir() if p.suffix == ".py"}
    found = set()
    for path in repo.rglob("*.py"):
        if set(path.relative_to(repo).parts) & SKIP_PARTS:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                top = name.split(".")[0]
                if top not in sys.stdlib_module_names and top not in local and top not in {"pytest", "_pytest"}:
                    found.add(top)
    return sorted(found)


def emit(fn):
    repo = Path(sys.argv[1]).resolve()
    try:
        passed, score, details = fn(repo)
        try:
            details["changed_files"] = changed_files(repo)
            details["non_stdlib_imports"] = non_stdlib_imports(repo)
        except Exception as exc:  # detail only
            details["meta_error"] = repr(exc)
        out = {"pass": bool(passed), "score": round(float(score), 3), "details": details}
    except Exception:
        out = {"pass": False, "score": 0.0, "details": {"checker_error": traceback.format_exc()[-2000:]}}
    print(json.dumps(out, ensure_ascii=False, default=str))


# ---------------------------------------------------------------- s6 specific
import csv
import random
import statistics
import unicodedata

N_PRODUCTS = 20000
N_QUERIES = 40

ADJ = ["Blue", "Red", "Large", "Small", "Classic", "Matte", "Glossy", "Vintage", "Compact", "Deluxe",
       "Crème", "Café", "Jalapeño", "Smoked", "Organic", "Nordic", "Rustic", "Slim", "Heavy", "Mini"]
MAT = ["Steel", "Oak", "Bamboo", "Glass", "Ceramic", "Copper", "Linen", "Wool", "Enamel", "Cast Iron",
       "Stoneware", "Porcelain", "Silicone", "Marble", "Walnut"]
ITEM = ["Mug", "Pan", "Knife", "Bowl", "Plate", "Teapot", "Kettle", "Grater", "Whisk", "Ladle", "Tray",
        "Jar", "Board", "Skillet", "Colander", "Spatula", "Tumbler", "Carafe", "Sieve", "Mortar"]
BRANDS = ["Müller", "Fjällräven", "Señor Frío", "Café Bleu", "Lodge", "Tefal", "Wüsthof", "Victorinox",
          "Crème & Co", "Øster", "Brötchen", "Hōjicha Works", "Acme", "Northwind", "Blue Fern"]
CATS = ["Kitchen", "Cookware", "Cutlery", "Tableware", "Gadgets", "Storage"]


def make_catalog(path: Path):
    rng = random.Random(1234)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sku", "name", "brand", "category", "price", "popularity"])
        for i in range(N_PRODUCTS):
            name = f"{rng.choice(ADJ)} {rng.choice(MAT)} {rng.choice(ITEM)} {rng.randint(1, 60)}cm"
            w.writerow([f"SKU-{i:05d}", name, rng.choice(BRANDS), rng.choice(CATS),
                        f"{rng.randint(300, 30000) / 100:.2f}", rng.randint(0, 5000)])


def make_queries():
    rng = random.Random(99)
    seen, out = set(), []
    pool = [w.lower() for w in ADJ + MAT + ITEM] + ["cafe", "creme", "jalapeno", "muller", "senor frio",
                                                    "oster", "hojicha", "cast iron", "WÜSTHOF", "fjallraven"]
    while len(out) < N_QUERIES + 1:
        q = " ".join(rng.sample(pool, rng.choice([1, 2, 2, 3])))
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _normalize(text):
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.casefold().split())


def oracle(catalog_path, queries, limit=20):
    with open(catalog_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    prepared = [(r["sku"], r["name"], int(r["popularity"]), _normalize(f"{r['name']} {r['brand']} {r['category']}"))
                for r in rows]
    out = {}
    for q in queries:
        terms = _normalize(q).split()
        hits = [p for p in prepared if all(t in p[3] for t in terms)]
        hits.sort(key=lambda p: (-p[2], p[1]))
        out[q] = [p[0] for p in hits[:limit]]
    return out


SNIPPET = r'''
import csv, json, os, statistics, sys, time, datetime as _dt
catalog = sys.argv[1]
queries = json.loads(sys.argv[2])

# Wall clocks that the checker can move forward (perf_counter is left alone for timing).
SHIFT = [0.0]
_real_time, _real_mono = time.time, time.monotonic
time.time = lambda: _real_time() + SHIFT[0]
time.monotonic = lambda: _real_mono() + SHIFT[0]
class _ShiftedDateTime(_dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return super().now(tz) + _dt.timedelta(seconds=SHIFT[0])
    @classmethod
    def utcnow(cls):
        return super().utcnow() + _dt.timedelta(seconds=SHIFT[0])
_dt.datetime = _ShiftedDateTime

# Machine-speed yardstick: one plain parse of the catalog file.
base = []
for _ in range(3):
    t = time.perf_counter()
    with open(catalog, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    base.append(time.perf_counter() - t)
baseline = min(base)

opens = [0]
def hook(event, args):
    if event == "open" and args and str(args[0]).endswith("catalog.csv"):
        opens[0] += 1
sys.addaudithook(hook)

from shop.search import search

def sku(p):
    return p["sku"] if isinstance(p, dict) else getattr(p, "sku")

results, times = {}, []
for q in queries:
    t = time.perf_counter()
    res = search(q)
    times.append(time.perf_counter() - t)
    results[q] = [sku(p) for p in res]
opens_during_queries = opens[0]

# The ERP rewrites the file while the service keeps running. An hour later a new product must show
# up, including in the results of a query that was already asked before the rewrite.
with open(catalog, newline="", encoding="utf-8") as fh:
    body = fh.read()
tmp_path = catalog + ".tmp"
with open(tmp_path, "w", newline="", encoding="utf-8") as fh:
    fh.write(body + "SKU-NEW01,Zanzibar " + queries[0].title() + " 30cm,Acme,Kitchen,9.99,99999\r\n")
os.replace(tmp_path, catalog)
future = _real_time() + 3600
os.utime(catalog, (future, future))
SHIFT[0] = 3600.0
fresh = {"repeat": [sku(p) for p in search(queries[0])][:1], "new": [sku(p) for p in search("zanzibar")]}
print(json.dumps({"baseline": baseline, "times": times, "opens": opens_during_queries, "results": results,
                  "after_update": fresh}))
'''


def check(repo: Path):
    details = {}
    tmp = Path(tempfile.mkdtemp(prefix="chk_s6_"))
    try:
        work = copy_repo(repo, tmp)
        catalog = work / "data" / "catalog.csv"
        catalog.parent.mkdir(exist_ok=True)
        make_catalog(catalog)
        queries = make_queries()
        want = oracle(catalog, queries)

        try:
            p = run([sys.executable, "-B", "-c", SNIPPET, str(catalog), json.dumps(queries)], work,
                    timeout=50, env_extra={"SHOP_CATALOG_PATH": str(catalog)})
        except subprocess.TimeoutExpired:
            details["error"] = "search run timed out after 50s"
            return False, 0.0, details
        lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
        try:
            r = json.loads(lines[-1])
        except Exception:
            details["error"] = (p.stderr or p.stdout)[-800:]
            return False, 0.0, details

        wrong = [q for q in queries if r["results"].get(q) != want[q]]
        details["results_correct"] = not wrong
        if wrong:
            details["wrong_queries"] = {q: [r["results"].get(q), want[q]] for q in wrong[:3]}

        baseline = r["baseline"]
        later = r["times"][1:]  # every query after the first is a distinct, never-seen query
        median = statistics.median(later)
        details["baseline_parse_ms"] = round(baseline * 1000, 2)
        details["first_query_ms"] = round(r["times"][0] * 1000, 2)
        details["median_query_ms"] = round(median * 1000, 3)
        details["median_query_vs_parse"] = round(median / baseline, 3)
        details["catalog_opens_for_%d_queries" % len(queries)] = r["opens"]
        # A query must not cost a re-read of the catalog: far fewer opens than queries, and each
        # distinct query cheaper than half of one plain CSV parse of the file.
        details["no_reread_per_query"] = r["opens"] <= 2
        details["distinct_queries_fast"] = median < 0.5 * baseline

        details["sees_catalog_update_within_an_hour"] = r.get("after_update") == {"repeat": ["SKU-NEW01"], "new": ["SKU-NEW01"]}
        if not details["sees_catalog_update_within_an_hour"]:
            details["after_update_got"] = r.get("after_update")

        ok_tests, tail = repo_tests(work)
        details["repo_tests_pass"] = ok_tests
        if not ok_tests:
            details["repo_tests_tail"] = tail

        gating = [details["results_correct"], details["no_reread_per_query"], details["distinct_queries_fast"],
                  details["sees_catalog_update_within_an_hour"]]
        allchecks = gating + [ok_tests]
        return all(gating), sum(allchecks) / len(allchecks), details
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    emit(check)
