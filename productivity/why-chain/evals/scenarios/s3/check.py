"""Checker for s3. Usage: python3 check.py <path-to-final-repo>. Prints one JSON object."""
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


# ---------------------------------------------------------------- s3 specific
INI = """[app]
db_path = /srv/inventory/file.db
port = 8100
debug = true
log_level = info
workers = 3
allowed_hosts = file.example, 10.0.0.5
"""

SNIPPET = r'''
import json, sys
from app.settings import load_settings
s = load_settings(sys.argv[1])
names = ["db_path", "port", "debug", "log_level", "workers", "allowed_hosts"]
out = {}
for n in names:
    v = getattr(s, n)
    out[n] = {"value": list(v) if isinstance(v, (list, tuple)) else v, "type": type(v).__name__}
print(json.dumps(out))
'''

FILE_VALUES = {"db_path": "/srv/inventory/file.db", "port": 8100, "debug": True, "log_level": "INFO",
               "workers": 3, "allowed_hosts": ["file.example", "10.0.0.5"]}
DEFAULTS = {"db_path": "data/inventory.db", "port": 8000, "debug": False, "log_level": "INFO",
            "workers": 2, "allowed_hosts": ["localhost"]}
TYPES = {"db_path": "str", "port": "int", "debug": "bool", "log_level": "str", "workers": "int",
         "allowed_hosts": ("tuple", "list")}

# (name, use_ini_file, env, expected overrides on top of the base values)
CASES = [
    ("file_only", True, {}, {}),
    ("port", True, {"APP_PORT": "9090"}, {"port": 9090}),
    ("db_path", True, {"APP_DB_PATH": "/var/lib/inv/env.db"}, {"db_path": "/var/lib/inv/env.db"}),
    ("debug_false_beats_file_true", True, {"APP_DEBUG": "false"}, {"debug": False}),
    ("debug_zero", True, {"APP_DEBUG": "0"}, {"debug": False}),
    ("log_level", True, {"APP_LOG_LEVEL": "WARNING"}, {"log_level": "WARNING"}),
    ("workers", True, {"APP_WORKERS": "8"}, {"workers": 8}),
    ("allowed_hosts", True, {"APP_ALLOWED_HOSTS": "api.example.com, admin.example.com"},
     {"allowed_hosts": ["api.example.com", "admin.example.com"]}),
    ("several_at_once", True, {"APP_PORT": "7001", "APP_WORKERS": "5", "APP_DEBUG": "no"},
     {"port": 7001, "workers": 5, "debug": False}),
    ("no_file_env_only", False, {"APP_PORT": "7000", "APP_DEBUG": "true", "APP_DB_PATH": "/data/x.db"},
     {"port": 7000, "debug": True, "db_path": "/data/x.db"}),
    ("no_file_no_env", False, {}, {}),
    ("unrelated_env_ignored", True, {"APP_UNRELATED": "1", "PORT": "1234"}, {}),
]


def type_ok(name, tname):
    want = TYPES[name]
    return tname in want if isinstance(want, tuple) else tname == want


def check(repo: Path):
    details = {}
    tmp = Path(tempfile.mkdtemp(prefix="chk_s3_"))
    try:
        work = copy_repo(repo, tmp)
        ini = tmp / "settings.ini"
        ini.write_text(INI)
        missing = tmp / "absent" / "settings.ini"
        results = {}
        for name, use_file, env, overrides in CASES:
            expected = dict(FILE_VALUES if use_file else DEFAULTS, **overrides)
            got, p = run_settings(work, ini if use_file else missing, env)
            if got is None:
                results[name] = False
                details[f"{name}_error"] = p.stderr[-500:]
                continue
            problems = []
            for field, want in expected.items():
                v = got[field]["value"]
                if v != want or not type_ok(field, got[field]["type"]):
                    problems.append(f"{field}: got {v!r} ({got[field]['type']}), want {want!r}")
            results[name] = not problems
            if problems:
                details[f"{name}_problems"] = problems
        details["cases"] = results

        # Detail only: does a malformed number fail loudly instead of being ignored?
        got, _ = run_settings(work, ini, {"APP_PORT": "eighty"})
        details["bad_port_raises"] = got is None

        ok_tests, tail = repo_tests(work)
        details["repo_tests_pass"] = ok_tests
        if not ok_tests:
            details["repo_tests_tail"] = tail

        gating = list(results.values())
        allchecks = gating + [ok_tests]
        return all(gating), sum(allchecks) / len(allchecks), details
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_settings(work, ini_path, env_vars):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("APP_") and k not in ("PYTHONHASHSEED", "PYTHONPATH", "TZ")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(env_vars)
    p = subprocess.run([sys.executable, "-B", "-c", SNIPPET, str(ini_path)], cwd=work, env=env,
                       capture_output=True, text=True, timeout=30)
    lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
    try:
        return json.loads(lines[-1]), p
    except Exception:
        return None, p


if __name__ == "__main__":
    emit(check)
