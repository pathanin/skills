#!/usr/bin/env python3
"""Grader calibration for the fresh-start evals.

Every saved version here is a target file whose correct verdicts were confirmed by running
it. `build` writes one throwaway eval case per version into <plugin>/evals-calib/, using the
real graders from evals/<case>/graders/. Checks that grade the agent's reply read the saved
reply from reply.txt instead, so the agent only has to say OK and can't refuse to recite a
claim. `check` compares a run's JSON with EXPECTED and exits 1 on any wrong verdict.

From the plugin directory (internal-tools/fresh-start):

    python3 evals/calibration/calibrate.py build
    claude plugin eval . --eval-dir evals-calib --runs 2 --ablation none --scaffold \
      --trust-plugin --judge-model sonnet -j 3 --no-publish --json evals-calib/result.json
    python3 evals/calibration/calibrate.py check evals-calib/result.json
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS = HERE.parent
OUT = EVALS.parent / "evals-calib"

TARGETS = {"finance-export": "shopkit/export.py", "tangled": "pricing.py", "clean-keep": "text.py"}

P, F = True, False
FE = ("plain-format", "atomic-write", "none-fields", "skips-test-orders", "country-column", "explains-format")
TG = ("free-shipping", "simpler", "no-flags")
CK = ("max-length", "old-lines-kept", "says-old-won")

# case -> version -> {grader: should it pass}
EXPECTED = {
    "finance-export": {
        "good": dict.fromkeys(FE, P),
        "good-csv": dict.fromkeys(FE, P),  # csv.writer with lineterminator="\n", mkstemp + os.replace
        "naive": dict.fromkeys(FE, F),  # csv defaults, direct write, .get defaults, case-sensitive skip
        "no-country": {**dict.fromkeys(FE, P), "country-column": F, "explains-format": F},  # a Sonnet run
    },
    "tangled": {
        "old": dict.fromkeys(TG, F),
        "inline": dict.fromkeys(TG, P),  # Opus; "if subtotal > 100: cost = 0.0"
        "helper": dict.fromkeys(TG, P),  # Opus; zone helper, "if subtotal <= 100: charge"
        "zero-after": dict.fromkeys(TG, P),  # Opus; judges failed its simpler check
        "per-branch": {"free-shipping": P, "simpler": F, "no-flags": P},  # Sonnet; weight charge per zone
        "at-100": {"free-shipping": F, "simpler": P, "no-flags": P},  # inline with >= 100
    },
    "clean-keep": {
        "keep": dict.fromkeys(CK, P),
        "rename": dict.fromkeys(CK, F),  # Sonnet; "light rewrite"
        "hybrid": dict.fromkeys(CK, F),  # Sonnet; called itself hybrid
        "fresh": dict.fromkeys(CK, F),  # Sonnet; fresh rewrite
    },
}

PROMPT = "---\nmodel: sonnet\nmax_turns: 2\ntimeout_seconds: 120\nallowed_tools: [Read]\n---\n\nReply with the single word OK.\n"
REPLY_FOCUS = "focus:\n  source: file\n  path: reply.txt\n"


def grader_for_calibration(case, name):
    text = (EVALS / case / "graders" / f"{name}.md").read_text()
    frontmatter = text.split("\n---", 1)[0]
    if "type: llm" in frontmatter and "focus:" not in frontmatter:
        return text.replace("type: llm\n", "type: llm\n" + REPLY_FOCUS, 1), True
    return text, False


def build():
    shutil.rmtree(OUT, ignore_errors=True)
    for case, versions in EXPECTED.items():
        for version, graders in versions.items():
            d = OUT / f"{case}--{version}"
            (d / "graders").mkdir(parents=True)
            files = {TARGETS[case]: (HERE / case / f"{version}.py").read_text()}
            needs_reply = False
            for name in graders:
                text, reads_reply = grader_for_calibration(case, name)
                (d / "graders" / f"{name}.md").write_text(text)
                needs_reply |= reads_reply
            if needs_reply:
                files["reply.txt"] = (HERE / case / f"{version}.reply.txt").read_text()
            script = ["#!/bin/bash", "set -e"]
            for path, body in files.items():
                assert "CALIB_EOF" not in body, path
                script += [f'mkdir -p "$(dirname {path})"', f"cat > {path} <<'CALIB_EOF'", body.rstrip("\n"), "CALIB_EOF"]
            (d / "fixture.sh").write_text("\n".join(script) + "\n")
            (d / "case.yaml").write_text(f'schema_version: "1.1"\nname: {case}--{version}\ncontext:\n  scaffold_script: fixture.sh\n')
            (d / "prompt.md").write_text(PROMPT)
    print(f"wrote {sum(len(v) for v in EXPECTED.values())} cases to {OUT}")


def check(path):
    result = json.loads(Path(path).read_text())
    wrong = seen = 0
    for c in result["cases"]:
        case, version = c["name"].split("--", 1)
        want = EXPECTED[case][version]
        for run in c["arms"]["with"]:
            for g in run["graders"]:
                seen += 1
                ok = g.get("passed") is want[g["name"]]
                wrong += not ok
                if not ok:
                    print(f"WRONG {case} {version} {g['name']}: want {'PASS' if want[g['name']] else 'FAIL'}, "
                          f"got {'PASS' if g.get('passed') else 'FAIL'} ({g.get('explanation', '')})")
    expected = sum(len(g) for v in EXPECTED.values() for g in v.values())
    print(f"{seen - wrong}/{seen} verdicts right; {expected} checks per run expected")
    sys.exit(1 if wrong or not seen else 0)


if __name__ == "__main__":
    if sys.argv[1:] == ["build"]:
        build()
    elif len(sys.argv) == 3 and sys.argv[1] == "check":
        check(sys.argv[2])
    else:
        sys.exit(__doc__)
