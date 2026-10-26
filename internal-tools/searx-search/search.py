#!/usr/bin/env python3
"""Query the local SearXNG instance, starting it first if it isn't running.

Usage: search.py "query" [-n 10] [--category general|news|it|science] [--json]
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.expanduser("~/.local/share/searxng")
PORT = int(os.environ.get("SEARXNG_PORT", "18888"))
BASE = f"http://127.0.0.1:{PORT}"


def is_up():
    try:
        urllib.request.urlopen(BASE + "/healthz", timeout=1)
        return True
    except Exception:
        return False


def start():
    if not os.path.isdir(ROOT):
        sys.exit(f"SearXNG not installed at {ROOT}")
    env = dict(os.environ, SEARXNG_SETTINGS_PATH=f"{ROOT}/settings.yml", SEARXNG_PORT=str(PORT))
    log = open(f"{ROOT}/server.log", "a")
    subprocess.Popen(
        [f"{ROOT}/venv/bin/python", "-m", "searx.webapp"],
        cwd=f"{ROOT}/src", env=env, stdout=log, stderr=log,
        stdin=subprocess.DEVNULL, start_new_session=True,
    )
    for _ in range(60):
        if is_up():
            return
        time.sleep(0.5)
    sys.exit(f"SearXNG did not start within 30s; see {ROOT}/server.log")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("query")
    p.add_argument("-n", type=int, default=10)
    p.add_argument("--category", default="general")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()

    if not is_up():
        start()
    qs = urllib.parse.urlencode({"q": a.query, "format": "json", "categories": a.category})
    with urllib.request.urlopen(f"{BASE}/search?{qs}", timeout=20) as r:
        data = json.load(r)
    results = data.get("results", [])[: a.n]

    if a.json:
        print(json.dumps(results, indent=2))
        return
    if not results:
        print("No results.", data.get("unresponsive_engines") or "")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.get('title', '')}\n   {r.get('url', '')}")
        if r.get("content"):
            print(f"   {r['content'][:300]}")
    if data.get("answers"):
        print("\nAnswers:", *[x.get("answer", x) if isinstance(x, dict) else x for x in data["answers"]], sep="\n")


if __name__ == "__main__":
    main()
