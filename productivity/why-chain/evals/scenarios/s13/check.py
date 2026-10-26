"""Standalone checker. Usage: python check.py <repo_dir>. Last stdout line is JSON."""
PROBE = r'''import json, os, sys, tempfile
from datetime import datetime, timedelta
repo = sys.argv[1]
sys.path.insert(0, repo)
res = {}
tmp = tempfile.mkdtemp(prefix="feed_")
FEED = os.path.join(tmp, "stop_times.csv")
ROWS = [
    ("9-0810", "9", "CENTRAL", "08:10:00"),
    ("9-0830", "9", "CENTRAL", "08:30:00"),
    ("9-0900", "9", "CENTRAL", "09:00:00"),
    ("9-2340", "9", "CENTRAL", "23:40:00"),
    ("N9-2400", "N9", "CENTRAL", "24:00:00"),
    ("N9-2415", "N9", "CENTRAL", "24:15:00"),
    ("N9-2505", "N9", "CENTRAL", "25:05:00"),
    ("9-0820", "9", "RIVERSIDE", "08:20:00"),
    ("9-0850", "9", "RIVERSIDE", "08:50:00"),
    ("N9-2415-R", "N9", "RIVERSIDE", "24:15:00"),
    ("BAD-CLOCK", "N9", "CENTRAL", "24:75:00"),
    ("BAD-TEXT", "N9", "CENTRAL", "not-a-time"),
]
with open(FEED, "w", newline="") as fh:
    fh.write("trip_id,route_id,stop_id,arrival_time\n")
    for row in ROWS:
        fh.write(",".join(row) + "\n")

def ids(board):
    return [a.trip_id for a in board]

def board(stop, now, hours):
    from nextbus.board import stop_board
    return stop_board(FEED, stop, now, horizon=timedelta(hours=hours))

try:
    res["daytime"] = ids(board("CENTRAL", datetime(2026, 5, 4, 8, 0), 2)) == [
        "9-0810", "9-0830", "9-0900"
    ]
    res["daytime_stop_filter"] = ids(board("RIVERSIDE", datetime(2026, 5, 4, 8, 0), 2)) == [
        "9-0820", "9-0850"
    ]
    res["late_evening"] = ids(board("CENTRAL", datetime(2026, 5, 4, 23, 30), 2)) == [
        "9-2340", "N9-2400", "N9-2415", "N9-2505"
    ]
    res["exact_midnight"] = ids(board("CENTRAL", datetime(2026, 5, 4, 23, 45), 0.75)) == [
        "N9-2400", "N9-2415"
    ]
    res["after_midnight"] = ids(board("CENTRAL", datetime(2026, 5, 5, 0, 5), 2)) == [
        "N9-2415", "N9-2505"
    ]
    res["after_midnight_riverside"] = ids(
        board("RIVERSIDE", datetime(2026, 5, 5, 0, 5), 2)
    ) == ["N9-2415-R"]
    res["horizon_window"] = ids(board("CENTRAL", datetime(2026, 5, 5, 0, 5), 0.4)) == [
        "N9-2415"
    ]
    res["no_past_trips"] = ids(board("CENTRAL", datetime(2026, 5, 4, 23, 50), 2)) == [
        "N9-2400", "N9-2415", "N9-2505"
    ]
    res["malformed_ignored"] = ids(board("CENTRAL", datetime(2026, 5, 5, 0, 5), 3)) == [
        "N9-2415", "N9-2505"
    ]
except Exception as e:
    res["error"] = repr(e)
print(json.dumps(res, default=str))
'''
REQUIRED = [
    'daytime',
    'daytime_stop_filter',
    'late_evening',
    'exact_midnight',
    'after_midnight',
    'after_midnight_riverside',
    'horizon_window',
    'no_past_trips',
]
WEIGHTS = REQUIRED + ['malformed_ignored']
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
