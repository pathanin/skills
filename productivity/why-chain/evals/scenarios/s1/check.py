"""Checker for s1. Usage: python3 check.py <path-to-final-repo>. Prints one JSON object."""
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
