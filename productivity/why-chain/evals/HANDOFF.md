# why-chain eval: handoff

Updated 2026-10-25 (second session). v1 and v2 are finished. **v3 is set up but not run.** Full results so far are in `RESULTS.md`.

## Where it stands

| Round | Skill wins | Turn-1 builds on controls (s1, s3, s5) | Turn-1 builds on symptoms (s2, s4, s6) | Checker passes |
|---|---|---|---|---|
| v1 | 2 of 6 (s1, s6) | 0/9 | 0/9 | 17/18 |
| v2 | 4 of 6 (s1, s3, s5, s6) | 9/9 | 0/9 | 18/18 |
| v3 | not run | – | – | – |

v2 was tuned by someone who had seen s1–s6, so it shows the fix took, not that it generalises. v3 is the generalisation test.

## Done this session

1. **The harness allowlist is fixed** (commit `afb4438`).
   - Runs now use the Bash sandbox plus `allow_bash_hook.py`, a PreToolUse hook that allows every Bash command except the deny list.
   - Smoke-tested on s4 base and s2 skill: loops, `VAR=… cmd`, heredocs and pytest all run, and both runs passed. Curl, git push and writes to the home folder stay blocked.
   - The one refusal left comes from the user's global `~/.claude` git-guard hook (on `git stash` / `git checkout --`). It hits both arms equally.
2. **v3 success criteria were written and committed before any run** (commit `47e64c8`, end of `RESULTS.md`).
3. **Five fresh scenarios, s7–s11**, were written by an isolated agent. Its tool calls never touched this repo, which was checked in its transcript.

   | id | type | summary |
   |---|---|---|
   | s7 | control | add `--dry-run` to a backup pruner |
   | s8 | control | ASCII-fold accented letters in `slugify`, stdlib only |
   | s9 | symptom | asks to dedupe; the real cause is an inclusive pagination cursor |
   | s10 | symptom | asks to raise a timeout; the real cause is an O(n²) list-membership dedupe |
   | s11 | wrong cause | blames a race and asks for a lock; the real cause is a double-applied discount |

   - **Checkers re-run by me:** 23 of 23 verdicts as expected (fixture fail, reference pass, naive fail, variants as named). Details are in `scenarios/INDEX_v3.md`.
   - `scenarios-v3-src/build.py` regenerates them.
   - `analyze.py` now counts s7 and s8 as controls.
   - `jobs_v3.txt` lists the 30 jobs.

## Next step: run v3 (about $30, about 25 min)

1. **Move the stale run data out.** `runs/` and `graders/` in `evals/` may hold old data. The two smoke-test runs live in the session scratchpad, not here.
2. **Copy `scenarios/` to a scratch folder outside the repo and run the jobs:**
   ```bash
   EVAL_DIR=<scratch>/eval xargs -P 12 -L 1 ./run_one.sh < jobs_v3.txt
   ```
   - Test one run first: check that `final.diff` isn't empty and that it has about 0 denials (`python3 runtrace.py --metrics …/turn1.jsonl`).
3. **Score the runs.** Copy them into `evals/runs/`, then run `/Users/oat/venv/bin/python3 score_and_blind.py`. Move the outputs into `v3/`.
4. **Grade with five fresh `general-purpose` agents, not forks.** Use `grader_prompt.md`, and give each agent only its scenario's `ground_truth.md` and the six packets, in an isolated folder.
   - Validate each `grades.json`.
   - grep the packets for phrases from `SKILL.md` to check the skill text didn't leak.
5. **Write up the results.** Run `python3 analyze.py v3`, then score the run against the criteria in `RESULTS.md` **as written**.

## Still open

- **s4 decision (owner):** should the skill build a *different* fix without asking when the evidence is strong? v3's s11 (wrong cause) will add evidence on this.
- **s1–s6 on the fixed harness:** not rerun, to save cost (about $36 for both arms). v1/v2 numbers are still from the old allowlist.
- **Packaging:** `evals/` ships inside the plugin folder. Move it if that matters.

## What's here

| Path | What it is |
|---|---|
| `RESULTS.md` | The report: v1, v2, and the v3 criteria. |
| `analyze.py <v1\|v2\|v3>` | Unblinds the grades and prints the tables. |
| `v1/`, `v2/` (gitignored) | The data from each round. |
| `run_one.sh`, `allow_bash_hook.py`, `jobs.txt`, `jobs_v3.txt`, `score_and_blind.py`, `grader_prompt.md`, `runtrace.py` | The harness. |
| `scenarios/` (s1–s11), `checker-src/`, `validation/`, `scenarios-v3-src/` | The scenarios and their checkers. |

## Lessons learned

- **Runs inside this repo** get every Edit and Write refused under headless `dontAsk`. Always use a scratch folder.
- **`score_and_blind.py` overwrites** `results.json`, `blind_key.json` and `graders/`, and `run_one.sh` deletes run folders with the same name. Archive the previous round first.
- **If `allow_bash_hook.py` can't be found,** every Bash call is denied silently and the agents blame "a broken hook". The script now resolves the hook's path before it changes directory.
