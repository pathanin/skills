"""Checker for s5. Usage: python3 check.py <path-to-final-repo>. Prints one JSON object."""
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


# ---------------------------------------------------------------- s5 specific
# The snippet patches time.sleep (and asyncio.sleep) *before* importing the repo, so any
# backoff is recorded instead of slept. Each case drives the worker's public drain().
SNIPPET = r'''
import json, sys, time, asyncio, urllib.error
SLEEPS = []
def fake_sleep(seconds):
    SLEEPS.append(float(seconds))
async def fake_async_sleep(seconds, *a, **k):
    SLEEPS.append(float(seconds))
time.sleep = fake_sleep
asyncio.sleep = fake_async_sleep

from notify.webhooks import Endpoint
from notify.worker import drain

def make_exc(name):
    return {
        "URLError": urllib.error.URLError(ConnectionRefusedError(61, "Connection refused")),
        "ConnectionRefusedError": ConnectionRefusedError(61, "Connection refused"),
        "ConnectionResetError": ConnectionResetError(54, "Connection reset by peer"),
        "TimeoutError": TimeoutError("timed out"),
    }[name]

class Script:
    def __init__(self, plan):
        self.plan = {k: list(v) for k, v in plan.items()}
        self.calls = []
    def __call__(self, url, body, headers, timeout):
        eid = headers.get("X-Event-Id")
        self.calls.append({"id": eid, "url": url, "body": body.decode() if isinstance(body, bytes) else str(body),
                           "headers": dict(headers)})
        steps = self.plan[eid]
        step = steps.pop(0) if len(steps) > 1 else steps[0]
        if isinstance(step, str):
            raise make_exc(step)
        return step

CASES = json.loads(sys.argv[1])
endpoint = Endpoint("https://partner.example/hooks", "s3cret")
out = {}
for name, plan in CASES.items():
    SLEEPS.clear()
    script = Script(plan)
    events = [{"id": eid, "type": "order.paid", "data": {"n": i}} for i, eid in enumerate(plan)]
    t0 = time.perf_counter()
    try:
        delivered, failed = drain(events, endpoint, transport=script)
        res = {"delivered": list(delivered), "failed": list(failed)}
    except BaseException as exc:
        res = {"raised": f"{type(exc).__name__}: {exc}"}
    res["calls"] = {eid: sum(1 for c in script.calls if c["id"] == eid) for eid in plan}
    per_id = {}
    for c in script.calls:
        h = c["headers"]
        per_id.setdefault(c["id"], set()).add(json.dumps([c["url"], c["body"], h.get("X-Event-Id"), h.get("X-Signature")]))
    res["requests_identical_across_attempts"] = all(len(v) == 1 for v in per_id.values())
    res["sleeps"] = list(SLEEPS)
    res["wall"] = time.perf_counter() - t0
    out[name] = res
print(json.dumps(out))
'''

# event id -> sequence of responses (int status or exception name); last entry repeats forever.
CASES = {
    "flap_then_ok": {"e1": [503, 502, 200]},
    "client_error": {"e1": [400]},
    "not_found": {"e1": [404]},
    "always_5xx": {"e1": [500]},
    "conn_error_then_ok": {"e1": ["URLError", 200]},
    "always_refused": {"e1": ["URLError"]},
    "reset_then_ok": {"e1": ["ConnectionResetError", 200]},
    "timeout_then_ok": {"e1": ["TimeoutError", 200]},
    "ok_first_time": {"e1": [200]},
    "mixed_batch": {"e1": [503, 201], "e2": [200], "e3": [504], "e4": [422]},
}


def judge(r):
    """Per-case expectations: (ok, reason)."""
    out = {}

    def ok(name, cond, why):
        out[name] = bool(cond)
        if not cond:
            out[name + "_why"] = why

    def res(name):
        return r.get(name, {})

    c = res("flap_then_ok")
    ok("flap_then_ok", c.get("delivered") == ["e1"] and c["calls"]["e1"] == 3, c)
    c = res("client_error")
    ok("client_error_not_retried", c.get("failed") == ["e1"] and c["calls"]["e1"] == 1, c)
    c = res("not_found")
    ok("not_found_not_retried", c.get("failed") == ["e1"] and c["calls"]["e1"] == 1, c)
    c = res("always_5xx")
    ok("always_5xx_three_attempts", c.get("failed") == ["e1"] and c["calls"]["e1"] == 3, c)
    c = res("conn_error_then_ok")
    ok("conn_error_retried", c.get("delivered") == ["e1"] and c["calls"]["e1"] == 2, c)
    c = res("always_refused")
    ok("always_refused_three_attempts", c.get("failed") == ["e1"] and c["calls"]["e1"] == 3, c)
    # Raw socket errors (not wrapped in URLError) are scored but do not gate the pass.
    c = res("reset_then_ok")
    ok("extra_raw_reset_retried", c.get("delivered") == ["e1"] and c["calls"]["e1"] == 2, c)
    c = res("timeout_then_ok")
    ok("extra_raw_timeout_retried", c.get("delivered") == ["e1"] and c["calls"]["e1"] == 2, c)
    c = res("ok_first_time")
    ok("success_no_retry_no_sleep", c.get("delivered") == ["e1"] and c["calls"]["e1"] == 1 and not c["sleeps"], c)
    c = res("mixed_batch")
    ok("mixed_batch", c.get("delivered") == ["e1", "e2"] and c.get("failed") == ["e3", "e4"]
       and c["calls"] == {"e1": 2, "e2": 1, "e3": 3, "e4": 1}, c)
    ok("same_request_each_attempt", all(v.get("requests_identical_across_attempts") for v in r.values()), "")

    # Backoff: a positive wait before each retry, bounded total.
    retried = [res("flap_then_ok"), res("always_5xx"), res("always_refused")]
    waits_ok = all(len([s for s in v.get("sleeps", []) if s > 0]) >= 2 for v in retried)
    bounded = all(sum(v.get("sleeps", [])) <= 60 for v in r.values())
    ok("waits_between_attempts", waits_ok and bounded, [v.get("sleeps") for v in retried])
    return out


def check(repo: Path):
    details = {}
    tmp = Path(tempfile.mkdtemp(prefix="chk_s5_"))
    try:
        work = copy_repo(repo, tmp)
        try:
            p = run([sys.executable, "-B", "-c", SNIPPET, json.dumps(CASES)], work, timeout=45)
        except subprocess.TimeoutExpired:
            details["error"] = "timed out (real sleeping or a hang?)"
            return False, 0.0, details
        lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
        try:
            r = json.loads(lines[-1])
        except Exception:
            details["error"] = (p.stderr or p.stdout)[-800:]
            return False, 0.0, details

        verdicts = judge(r)
        details["cases"] = {k: v for k, v in verdicts.items() if not k.endswith("_why")}
        details["failures"] = {k: v for k, v in verdicts.items() if k.endswith("_why")}
        sleeps = r.get("always_5xx", {}).get("sleeps", [])
        details["sleeps_always_5xx"] = sleeps
        # Detail only: exponential growth (jitter can legitimately break this).
        details["backoff_grows"] = len(sleeps) >= 2 and sleeps[-1] > sleeps[0]
        details["max_case_wall_s"] = round(max(v.get("wall", 0) for v in r.values()), 3)

        ok_tests, tail = repo_tests(work)
        details["repo_tests_pass"] = ok_tests
        if not ok_tests:
            details["repo_tests_tail"] = tail

        gating = [v for k, v in details["cases"].items() if not k.startswith("extra_")]
        allchecks = list(details["cases"].values()) + [ok_tests]
        return all(gating), sum(allchecks) / len(allchecks), details
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    emit(check)
