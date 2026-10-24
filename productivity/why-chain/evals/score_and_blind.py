"""Score every run with its scenario checker, collect metrics, and write blinded packets.

Usage: python3 score_and_blind.py
Writes: results.json (unblinded, for analysis), blind_key.json (id -> run),
        graders/<scenario>/<id>.md (blinded packets for the graders).
"""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

E = Path(__file__).resolve().parent
sys.path.insert(0, str(E))
import runtrace as tr  # noqa: E402

RUN_RE = re.compile(r"(s\d+)_(skill|base)_(\d+)")


def check(scenario, repo):
    p = subprocess.run(
        [sys.executable, str(E / "scenarios" / scenario / "check.py"), str(repo)],
        capture_output=True, text=True, timeout=600,
    )
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"pass": False, "score": 0.0, "details": {"checker_error": p.stderr[-800:] or p.stdout[-800:]}}


def scrub(text, run_dir):
    text = text.replace(str(run_dir / "repo"), "<repo>").replace(str(run_dir), "<run>")
    text = text.replace(str(E), "<eval>")
    return RUN_RE.sub("<run>", text).replace("/why-chain", "")


def main():
    results = []
    for run_dir in sorted((E / "runs").iterdir()):
        m = RUN_RE.fullmatch(run_dir.name)
        if not m:
            continue
        s, arm, rep = m.groups()
        t1 = tr.metrics(run_dir / "turn1.jsonl") if (run_dir / "turn1.jsonl").exists() else {}
        t2 = tr.metrics(run_dir / "turn2.jsonl") if (run_dir / "turn2.jsonl").exists() else {}
        after1 = (run_dir / "after_turn1.txt").read_text()
        commits1 = int(re.search(r"commits_after_initial=(\d+)", after1).group(1))
        changed1 = [ln for ln in after1.splitlines()[1:] if ln.strip()]
        results.append({
            "run": run_dir.name, "scenario": s, "arm": arm, "rep": int(rep),
            "check": check(s, run_dir / "repo"),
            "changed_repo_in_turn1": commits1 > 1 or bool(changed1),
            "cost_usd": (t1.get("cost_usd") or 0) + (t2.get("cost_usd") or 0),
            "turns": (t1.get("num_turns") or 0) + (t2.get("num_turns") or 0),
            "duration_s": ((t1.get("duration_ms") or 0) + (t2.get("duration_ms") or 0)) / 1000,
            "denials": (t1.get("denials") or 0) + (t2.get("denials") or 0),
            "errors": bool(t1.get("is_error")) or bool(t2.get("is_error")) or not t2,
        })
    (E / "results.json").write_text(json.dumps(results, indent=1))

    rng = random.Random(20261024)
    key = {}
    for s in sorted({r["scenario"] for r in results}):
        out = E / "graders" / s
        out.mkdir(parents=True, exist_ok=True)
        runs = [r for r in results if r["scenario"] == s]
        rng.shuffle(runs)
        req = (E / "scenarios" / s / "request.txt").read_text().strip()
        fol = (E / "scenarios" / s / "followup.txt").read_text().strip()
        for i, r in enumerate(runs):
            rid = f"{s}-{chr(65 + i)}"
            key[rid] = r["run"]
            rd = E / "runs" / r["run"]
            diff = (rd / "final.diff").read_text()
            diff_lines = diff.splitlines()
            if len(diff_lines) > 400:
                diff = "\n".join(diff_lines[:400]) + f"\n…[{len(diff_lines) - 400} more lines]"
            after1 = (rd / "after_turn1.txt").read_text()
            body = [
                f"# Run {rid}",
                f"## User message 1\n\n{req}",
                "## Agent turn 1 (trace)\n\n" + tr.trace(rd / "turn1.jsonl"),
                "## Repo state when the agent ended turn 1 (measured by the harness)\n\n"
                + ("The agent HAD changed the repo before the user replied:\n" if r["changed_repo_in_turn1"]
                   else "The repo was unchanged when the agent ended turn 1.\n") + "```\n" + after1 + "```",
                f"## User message 2\n\n{fol}",
                "## Agent turn 2 (trace)\n\n" + (tr.trace(rd / "turn2.jsonl") if (rd / "turn2.jsonl").exists() else "(missing)"),
                "## Final diff against the starting repo\n\n```diff\n" + diff + "\n```",
            ]
            (out / f"{rid}.md").write_text(scrub("\n\n".join(body), rd))
    (E / "blind_key.json").write_text(json.dumps(key, indent=1))
    print(f"{len(results)} runs scored; packets in {E / 'graders'}")


if __name__ == "__main__":
    main()
