"""Unblind the grades and print per-scenario tables as Markdown.

Usage: python3 analyze.py
Reads: results.json, blind_key.json, graders/<s>/grades.json (all written earlier).
"""
import json
from pathlib import Path
from statistics import mean

E = Path(__file__).resolve().parent
DIMS = ["diagnosis", "evidence", "verification", "proportion", "communication"]
ARMS = ["skill", "base"]
CONTROLS = {"s1", "s3", "s5"}


def fmt(xs):
    return f"{mean(xs):.1f}" if xs else "–"


def main():
    results = {r["run"]: r for r in json.loads((E / "results.json").read_text())}
    key = json.loads((E / "blind_key.json").read_text())
    for rid, run in key.items():
        s = rid.split("-")[0]
        g = json.loads((E / "graders" / s / "grades.json").read_text())
        # A grader may write the bare letter ("A") instead of the full id ("s2-A").
        gid = rid if rid in g["runs"] else rid.split("-")[1]
        results[run]["grade"] = g["runs"][gid]
        results[run]["rank"] = g["ranking"].index(gid) + 1
        results[run]["id"] = rid

    scenarios = sorted({r["scenario"] for r in results.values()})
    by = {(s, a): [r for r in results.values() if r["scenario"] == s and r["arm"] == a]
          for s in scenarios for a in ARMS}

    print("## Checker scripts (final repo)\n")
    print("| scenario | type | skill pass | base pass | skill score | base score |")
    print("|---|---|---|---|---|---|")
    for s in scenarios:
        k, b = by[s, "skill"], by[s, "base"]
        typ = "control" if s in CONTROLS else "symptom"
        print(f"| {s} | {typ} | {sum(r['check']['pass'] for r in k)}/{len(k)} | "
              f"{sum(r['check']['pass'] for r in b)}/{len(b)} | "
              f"{fmt([r['check']['score'] for r in k])} | {fmt([r['check']['score'] for r in b])} |")

    print("\n## LLM graders (process, mean of 3 runs, 1–5; rank 1 = best of 6)\n")
    print("| scenario | arm | " + " | ".join(DIMS) + " | mean rank | ranks |")
    print("|---|---|" + "---|" * (len(DIMS) + 2))
    for s in scenarios:
        for a in ARMS:
            rs = by[s, a]
            dims = " | ".join(fmt([r["grade"][d] for r in rs]) for d in DIMS)
            ranks = sorted(r["rank"] for r in rs)
            print(f"| {s} | {a} | {dims} | {fmt(ranks)} | {', '.join(map(str, ranks))} |")

    print("\n## Behaviour and overhead (mean per run)\n")
    print("| scenario | arm | changed repo in turn 1 | cost $ | turns | wall s | denials |")
    print("|---|---|---|---|---|---|---|")
    for s in scenarios:
        for a in ARMS:
            rs = by[s, a]
            print(f"| {s} | {a} | {sum(r['changed_repo_in_turn1'] for r in rs)}/{len(rs)} | "
                  f"{mean(r['cost_usd'] for r in rs):.2f} | {fmt([r['turns'] for r in rs])} | "
                  f"{mean(r['duration_s'] for r in rs):.0f} | {fmt([r['denials'] for r in rs])} |")
    for a in ARMS:
        rs = [r for r in results.values() if r["arm"] == a]
        print(f"| **all** | {a} | {sum(r['changed_repo_in_turn1'] for r in rs)}/{len(rs)} | "
              f"{mean(r['cost_usd'] for r in rs):.2f} | {fmt([r['turns'] for r in rs])} | "
              f"{mean(r['duration_s'] for r in rs):.0f} | {fmt([r['denials'] for r in rs])} |")

    print("\n## Per-run grader notes\n")
    for s in scenarios:
        for a in ARMS:
            for r in sorted(by[s, a], key=lambda r: r["rep"]):
                g = r["grade"]
                print(f"- **{r['run']}** ({r['id']}, rank {r['rank']}): {g['note']}")


if __name__ == "__main__":
    main()
