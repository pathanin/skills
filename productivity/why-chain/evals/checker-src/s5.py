

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
