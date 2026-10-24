# why-chain eval: handoff

Updated 2026-10-25. The A/B eval of `/why-chain` has two finished rounds: v1 (the original skill) and v2 (revised skill, commit `2809e9a`). Full results are in `RESULTS.md`.

## Where it stands

| Round | Skill wins | Turn-1 builds on controls (s1, s3, s5) | Turn-1 builds on symptoms (s2, s4, s6) | Checker passes |
|---|---|---|---|---|
| v1 | 2 of 6 (s1, s6) | 0/9 | 0/9 | 17/18 |
| v2 | 4 of 6 (s1, s3, s5, s6) | 9/9 | 0/9 | 18/18 |

- **v2 met every success criterion** written before its runs.
- **Still losing:**
  - **s4**, where the user named the wrong cause: the baseline just fixes it, while the skill shows the chain and asks first.
  - **s2**, slightly: the baseline finds the root on its own.
- **v2 was tuned by someone who had seen these scenarios,** so the v2 result shows the fix took, not that it generalises.

## What's here

| Path | What it is |
|---|---|
| `RESULTS.md` | The report. v1 verdict and caveats, the v2 success criteria (written before the runs), v2 results. |
| `analyze.py <v1\|v2>` | Unblinds the grades and prints the per-scenario tables. |
| `v1/`, `v2/` (gitignored, local only) | `runs/`, `results.json`, `blind_key.json` and `graders/<s>/grades.json` for each round. v2's `runs/` holds the new skill runs plus copies of the v1 baseline runs. |
| `run_one.sh`, `jobs.txt`, `score_and_blind.py`, `grader_prompt.md`, `runtrace.py` | The harness; unchanged from v1 apart from a comment in `run_one.sh`. |
| `scenarios/`, `checker-src/`, `validation/` | The six scenarios and their checkers. |

## How to run a round (lessons learned)

1. **Run outside the repo.** Copy `scenarios/` into a scratch folder and set `EVAL_DIR` to it. Runs inside this repo had every Edit and Write refused under headless `dontAsk`, which wasted one full v2 batch (about $15).
   ```bash
   EVAL_DIR=<scratch>/eval xargs -P 12 -L 1 ./run_one.sh < jobs.txt
   ```
   Test one run first and check that its `final.diff` isn't empty.
2. **Copy the runs back and score them.** Copy the run folders into `evals/runs/`, then run `score_and_blind.py` with `/Users/oat/venv/bin/python3` (the checkers need pytest).
3. **Move the previous round's data into `vN/` first.** `score_and_blind.py` overwrites `results.json`, `blind_key.json` and `graders/`, and `run_one.sh` deletes existing run folders of the same name.
4. **Grade with six fresh `general-purpose` agents.** Not forks, because a fork inherits the unblinded context.
   - Give each one a copy of only its scenario's `ground_truth.md` and the six packets, in an isolated scratch folder.
   - Validate each `grades.json`: six IDs, five scores from 1–5 per run, and a ranking that uses all six IDs once.
5. **Check that the skill text didn't leak into the packets.** `grep` a few distinctive phrases from `SKILL.md` across `graders/*/*.md`.
6. **Cost:** about $1 per run. An 18-run skill-only round is about $18 and 15 minutes at 12 in parallel.

## Open next steps (none started)

1. **Test generalisation.** Have an independent agent, one that never sees the skill, `RESULTS.md` or these scenarios, write 3–6 fresh scenarios. Then run both arms on them. This is the only way to show v2 isn't just fitted to s1–s6.
2. **Decide on s4.** To win s4, the skill would need to build a *different* fix than the one requested, without asking, when the evidence is strong. That removes the user's chance to say no to a change of course. It's a judgement call for the skill's owner, not a bug.
3. **Fix the harness allowlist,** then rerun both arms. Shell commands like `for` loops, `VAR=… cmd` and some `python3`/`git` forms were refused, which held back verification in both arms (see the v1 caveats). Changing the allowlist means rerunning the baseline too, so the arms stay comparable.
4. **Packaging.** `evals/` sits inside the plugin folder, so it ships with the plugin. It is committed there now. Move it if that matters.
