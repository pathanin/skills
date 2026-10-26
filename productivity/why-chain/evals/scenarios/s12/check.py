"""Standalone checker. Usage: python check.py <repo_dir>. Last stdout line is JSON."""
PROBE = r'''import json, sys, threading, time

repo = sys.argv[1]
sys.path.insert(0, repo)
res = {}

from hookrelay.events import Event
from hookrelay.handlers import HandlerRegistry, UnknownEventType
from hookrelay.relay import Relay


def make_relay(handler, event_type="work"):
    registry = HandlerRegistry()
    registry.register(event_type, handler)
    return Relay(registry=registry)


def sequential_probe():
    calls = []

    def handler(event):
        calls.append(event.id)
        return {"n": len(calls)}

    relay = make_relay(handler)
    event = Event("evt_seq", "work", {})
    first = relay.handle(event)
    second = relay.handle(event)
    third = relay.handle(event)
    replayed = relay.handle(Event("evt_seq", "work", {"replayed": True}))
    once = len(calls) == 1
    return {
        "sequential_once": once,
        "sequential_same_receipt": second == first and third == first,
        "same_id_ignores_payload": once and replayed == first,
        "sequential_stats_once": relay.stats.count_for("work") == 1,
    }


def retry_probe():
    attempts = []

    def handler(event):
        attempts.append(1)
        if len(attempts) < 2:
            raise RuntimeError("downstream is down")
        return {"attempt": len(attempts)}

    relay = make_relay(handler)
    event = Event("evt_retry", "work", {})
    raised = False
    try:
        relay.handle(event)
    except RuntimeError:
        raised = True
    no_receipt = relay.receipts.get("evt_retry") is None
    second = relay.handle(event)
    third = relay.handle(event)
    return {
        "failure_propagates": raised,
        "failed_not_receipted": no_receipt,
        "retry_after_failure": len(attempts) == 2 and second.result == {"attempt": 2},
        "retry_cached": len(attempts) == 2 and third == second,
    }


def double_failure_probe():
    attempts = []

    def handler(event):
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("still down")
        return {"attempt": len(attempts)}

    relay = make_relay(handler)
    event = Event("evt_retry2", "work", {})
    for _ in range(2):
        try:
            relay.handle(event)
        except RuntimeError:
            pass
    receipt = relay.handle(event)
    return {
        "two_failures_then_success": len(attempts) == 3
        and receipt.result == {"attempt": 3}
    }


def concurrency_probe():
    started = threading.Event()
    release = threading.Event()
    calls = []

    def handler(event):
        calls.append(1)
        call_number = len(calls)
        started.set()
        release.wait(10)
        return {"call": call_number}

    relay = make_relay(handler)
    event = Event("evt_conc", "work", {})
    results = []
    errors = []

    def worker():
        try:
            results.append(relay.handle(event))
        except BaseException as exc:
            errors.append(repr(exc))

    first = threading.Thread(target=worker)
    first.start()
    if not started.wait(10):
        release.set()
        return {
            "concurrent_once": False,
            "concurrent_same_result": False,
            "concurrency_error": "handler never started",
        }

    barrier = threading.Barrier(5)

    def duplicate():
        try:
            barrier.wait(10)
        except Exception:
            pass
        worker()

    others = [threading.Thread(target=duplicate) for _ in range(5)]
    for thread in others:
        thread.start()
    time.sleep(0.5)
    release.set()
    first.join(10)
    for thread in others:
        thread.join(10)

    same = (
        len(results) == 6
        and not errors
        and all(receipt == results[0] for receipt in results)
    )
    return {
        "concurrent_once": len(calls) == 1,
        "concurrent_same_result": same,
    }


def routing_probe():
    calls = []

    def handler(event):
        calls.append(event.id)
        return {"id": event.id}

    relay = make_relay(handler)
    relay.handle(Event("evt_a", "work", {}))
    relay.handle(Event("evt_b", "work", {}))
    distinct = len(calls) == 2 and calls == ["evt_a", "evt_b"]

    plain = Relay()
    try:
        plain.handle(Event("evt_unknown", "nope", {}))
        unknown = False
    except UnknownEventType:
        unknown = plain.receipts.get("evt_unknown") is None
    return {"distinct_events": distinct, "unknown_type": unknown}


for probe in (
    sequential_probe,
    retry_probe,
    double_failure_probe,
    concurrency_probe,
    routing_probe,
):
    try:
        res.update(probe())
    except Exception as exc:
        res[probe.__name__ + "_error"] = type(exc).__name__ + ": " + str(exc)

print(json.dumps(res, default=str))
'''
REQUIRED = [
    'sequential_once',
    'sequential_same_receipt',
    'retry_after_failure',
    'retry_cached',
    'concurrent_once',
    'concurrent_same_result',
    'distinct_events',
    'unknown_type',
]
WEIGHTS = REQUIRED + [
    'same_id_ignores_payload',
    'sequential_stats_once',
    'failure_propagates',
    'failed_not_receipted',
    'two_failures_then_success',
]
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
