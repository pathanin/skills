#!/usr/bin/env python3
"""Run the worktree-swarm eval cases with `claude -p`, with and without the skill, and grade them.

`claude plugin eval` refuses `isolation: "worktree"` inside its harness, which is the mechanism this
skill exists to drive. This runner reads the same case files (fixture.sh, prompt.md, graders/*.md)
and grades them the same way, but launches a plain `claude -p` session per run so worktrees work.

    python3 evals/run.py                       # every case, 3 runs, both arms
    python3 evals/run.py --case fanout-six --runs 1 --arms with

Stdlib only. Runs as you, unsandboxed, in a fresh temp repo per run: only run cases you trust.
Results go to evals/results/<timestamp>/ (gitignored).
"""
import argparse
import concurrent.futures as cf
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

EVALS = Path(__file__).resolve().parent
SKILL_DIR = EVALS.parent
PRINT_LOCK = threading.Lock()


def log(msg):
    with PRINT_LOCK:
        print(msg, flush=True)


# ---------- case files ----------

def parse_scalar(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [parse_scalar(x) for x in v[1:-1].split(",") if x.strip()]
    if v.startswith("{") and v.endswith("}"):
        out = {}
        for part in v[1:-1].split(","):
            k, _, val = part.partition(":")
            out[k.strip()] = parse_scalar(val)
        return out
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    if v in ("true", "false"):
        return v == "true"
    return v


def read_md(path):
    """Split a `---` frontmatter file into (flat dict, body)."""
    text = path.read_text()
    meta, body = {}, text
    if text.startswith("---\n"):
        head, _, body = text[4:].partition("\n---\n")
        for line in head.splitlines():
            if line.strip() and not line.startswith(" "):
                k, _, v = line.partition(":")
                meta[k.strip()] = parse_scalar(v)
    return meta, body.strip()


def load_case(case_dir):
    meta, prompt = read_md(case_dir / "prompt.md")
    graders = []
    for g in sorted((case_dir / "graders").glob("*.md")):
        gm, body = read_md(g)
        gm["name"] = g.stem
        gm["body"] = body
        graders.append(gm)
    return {"name": case_dir.name, "dir": case_dir, "meta": meta, "prompt": prompt, "graders": graders}


# ---------- one run ----------

def run_agent(case, arm, run_dir):
    # The repo lives in a temp dir outside this checkout: nested inside it, edits get refused.
    run_dir.mkdir(parents=True)
    repo = Path(tempfile.mkdtemp(prefix=f"swarm-{case['name']}-{arm}-"))
    (run_dir / "repo").symlink_to(repo)
    subprocess.run(["bash", str(case["dir"] / "fixture.sh")], cwd=repo, check=True,
                   capture_output=True)
    m = case["meta"]
    cmd = ["claude", "-p", case["prompt"], "--output-format", "stream-json", "--verbose",
           "--max-turns", str(m.get("max_turns", 100)),
           "--allowedTools", ",".join(m.get("allowed_tools", [])), "--permission-mode", "acceptEdits"]
    if m.get("model"):
        cmd += ["--model", m["model"]]
    if arm == "with":
        cmd += ["--plugin-dir", str(SKILL_DIR)]
    start = time.time()
    timed_out = False
    with open(run_dir / "trace.jsonl", "w") as out, open(run_dir / "stderr.txt", "w") as err:
        p = subprocess.Popen(cmd, cwd=repo, stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                             start_new_session=True)
        try:
            p.wait(timeout=m.get("timeout_seconds", 1800))
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(p.pid, 9)
            p.wait()
    return {"seconds": round(time.time() - start), "timed_out": timed_out, "exit": p.returncode}


def parse_trace(path):
    """Top-level tool calls (with whether their result was an error), final text, cost."""
    calls, by_id, final, cost, turns = [], {}, "", None, None
    for line in path.read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            final = ev.get("result") or final
            cost = ev.get("total_cost_usd")
            turns = ev.get("num_turns")
        if ev.get("parent_tool_use_id"):
            continue  # a subagent's own messages
        msg = ev.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            continue
        for b in content:
            if ev.get("type") == "assistant" and b.get("type") == "tool_use":
                c = {"name": b["name"], "input": b.get("input", {}), "error": False}
                calls.append(c)
                by_id[b["id"]] = c
            elif ev.get("type") == "assistant" and b.get("type") == "text":
                final = b["text"]
            elif ev.get("type") == "user" and b.get("type") == "tool_result" and b.get("tool_use_id") in by_id:
                text = b["content"] if isinstance(b["content"], str) else json.dumps(b["content"])
                c = by_id[b["tool_use_id"]]
                c["error"] = bool(b.get("is_error")) or text.startswith("Cannot create agent")
                c["result"] = text[:500]
    return calls, final, cost, turns


# ---------- graders ----------

def js_input_text(inp):
    # JSON.stringify layout: no spaces, raw unicode. Grader regexes are written against it.
    return json.dumps(inp, separators=(",", ":"), ensure_ascii=False)


def grade_tool_used(g, calls):
    rx = re.compile(g["input_match"]) if g.get("input_match") else None
    n = sum(1 for c in calls if c["name"] == g["tool"] and not c["error"]
            and (rx is None or rx.search(js_input_text(c["input"]))))
    lo, hi = g.get("min", 1), g.get("max", float("inf"))
    return lo <= n <= hi, f"{g['tool']} matched {n}x (expected {lo}..{hi})"


def grade_regex(g, repo, final):
    target = g.get("target", "last_message")
    if isinstance(target, dict):
        f = repo / target["path"]
        if not f.exists():
            return False, f"{target['path']} does not exist"
        text = f.read_text(errors="replace")
    else:
        text = final
    hits = re.findall(g.get("pattern") or g["body"], text, re.M if "m" in g.get("flags", "") else 0)
    match = g.get("match", "contains")
    if match == "contains":
        return bool(hits), f"{len(hits)} matches"
    if match == "not_contains":
        return not hits, f"{len(hits)} matches"
    want = int(match.split(":")[1])
    return len(hits) == want, f"{len(hits)} matches (expected {want})"


def grade_llm(g, final, judge_model):
    prompt = ("You are grading the output of a coding agent against a criterion.\nCriterion:\n"
              f"{g['body']}\nAgent output (last_message):\n{final}\n"
              "Respond with exactly one word: PASS or FAIL.")
    votes = []
    for _ in range(3):
        r = subprocess.run(["claude", "-p", prompt, "--model", judge_model, "--tools", ""],
                           capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL,
                           cwd=tempfile.gettempdir())  # keep the repo's CLAUDE.md out of the judge
        out = r.stdout
        votes.append(bool(re.search(r"\bPASS\b", out)) and not re.search(r"\bFAIL\b", out))
    return sum(votes) > len(votes) / 2, "judge votes: " + " ".join("PASS" if v else "FAIL" for v in votes)


def grade(case, run_dir, judge_model):
    calls, final, cost, turns = parse_trace(run_dir / "trace.jsonl")
    repo = run_dir / "repo"
    results = []
    for g in case["graders"]:
        try:
            if g["type"] == "tool_used":
                ok, why = grade_tool_used(g, calls)
            elif g["type"] == "regex":
                ok, why = grade_regex(g, repo, final)
            elif g["type"] == "llm":
                ok, why = grade_llm(g, final, judge_model)
            else:
                ok, why = False, f"unsupported grader type {g['type']}"
        except Exception as e:  # a broken grader is a red, not a crash
            ok, why = False, f"grader error: {e}"
        results.append({"name": g["name"], "passed": ok, "weight": g.get("weight", 1), "why": why})
    total = sum(r["weight"] for r in results)
    score = sum(r["weight"] for r in results if r["passed"]) / total if total else 0
    agents = [{k: c["input"].get(k) for k in ("description", "model", "effort", "isolation", "subagent_type")}
              | {"error": c["error"]} for c in calls if c["name"] == "Agent"]
    return {"score": round(score, 3), "graders": results, "cost_usd": cost, "turns": turns,
            "agents": agents, "final": final[-3000:]}


# ---------- driver ----------

def one(case, arm, n, out_root, judge_model):
    run_dir = out_root / case["name"] / f"{arm}-{n}"
    log(f"start  {case['name']} {arm} #{n}")
    info = run_agent(case, arm, run_dir)
    res = grade(case, run_dir, judge_model) | info | {"case": case["name"], "arm": arm, "run": n}
    (run_dir / "result.json").write_text(json.dumps(res, indent=2))
    # worktrees are full checkouts; keep the graded files, drop the rest
    for wt in (run_dir / "repo" / ".claude" / "worktrees").glob("*"):
        shutil.rmtree(wt, ignore_errors=True)
    log(f"done   {case['name']} {arm} #{n}: score {res['score']} cost ${res['cost_usd']} "
        f"{info['seconds']}s{' TIMEOUT' if info['timed_out'] else ''}")
    return res


def summarize(results, cases, arms):
    lines = []
    for case in cases:
        rs = [r for r in results if r["case"] == case["name"]]
        if not rs:
            continue
        lines.append(f"\n### {case['name']}\n")
        head = "| check | " + " | ".join(arms) + " |"
        lines += [head, "|---|" + "---|" * len(arms)]
        for g in case["graders"]:
            row = [g["name"]]
            for arm in arms:
                ar = [r for r in rs if r["arm"] == arm]
                p = sum(1 for r in ar for x in r["graders"] if x["name"] == g["name"] and x["passed"])
                row.append(f"{p}/{len(ar)}" if ar else "-")
            lines.append("| " + " | ".join(row) + " |")
        row = ["**score (mean)**"]
        for arm in arms:
            ar = [r for r in rs if r["arm"] == arm]
            row.append(f"{sum(r['score'] for r in ar) / len(ar):.2f}" if ar else "-")
        lines.append("| " + " | ".join(row) + " |")
        row = ["cost (sum, $)"]
        for arm in arms:
            ar = [r for r in rs if r["arm"] == arm]
            row.append(f"{sum(r['cost_usd'] or 0 for r in ar):.2f}" if ar else "-")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", action="append", help="case name (repeatable); default all")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--arms", default="with,without", help="with, without, or both comma-separated")
    ap.add_argument("-j", type=int, default=2, help="runs at once (each is a full claude session)")
    ap.add_argument("--judge-model", default="sonnet")
    ap.add_argument("--out", help="output dir (default evals/results/<timestamp>)")
    a = ap.parse_args()

    names = a.case or sorted(p.name for p in EVALS.iterdir() if (p / "prompt.md").exists())
    cases = [load_case(EVALS / n) for n in names]
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    out_root = Path(a.out) if a.out else EVALS / "results" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_root.mkdir(parents=True, exist_ok=True)
    jobs = [(c, arm, n) for c in cases for n in range(1, a.runs + 1) for arm in arms]
    log(f"{len(jobs)} runs -> {out_root}")
    results = []
    with cf.ThreadPoolExecutor(max_workers=a.j) as ex:
        futs = [ex.submit(one, c, arm, n, out_root, a.judge_model) for c, arm, n in jobs]
        for f in cf.as_completed(futs):
            try:
                results.append(f.result())
            except Exception as e:
                log(f"run failed: {e}")
    results.sort(key=lambda r: (r["case"], r["arm"], r["run"]))
    (out_root / "summary.json").write_text(json.dumps(results, indent=2))
    table = summarize(results, cases, arms)
    total = sum(r["cost_usd"] or 0 for r in results)
    (out_root / "summary.md").write_text(f"# worktree-swarm eval {out_root.name}\n\nTotal cost ${total:.2f}\n{table}\n")
    print(table)
    print(f"\nTotal agent cost ${total:.2f} (judge calls not included). Details: {out_root}")


if __name__ == "__main__":
    sys.exit(main())
