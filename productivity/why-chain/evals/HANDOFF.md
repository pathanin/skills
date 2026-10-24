# why-chain eval: handoff

Written 2026-10-24. This is an A/B evaluation of the `/why-chain` skill. It is about half done: the runs exist but have not been scored or graded yet.

## Goal

Measure whether `/why-chain` makes Claude Code handle tasks better than plain Claude Code does, without context bias:
- the scenarios were written by an independent agent that never saw the skill;
- each run is a separate headless `claude -p` process;
- grading is done by blind, independent agents.

## Status

| Step | State |
|---|---|
| 1. Scenarios, ground truth, checkers | **Done.** 6 scenarios, all checkers validated (details below). |
| 2. Runs: 6 scenarios × 2 arms × 3 reps = 36 | **Ran.** They should be in `runs/` (see "If runs/ is missing"). |
| 3. Score final repos with checkers + blind the traces | **Not done.** |
| 4. Grade process quality with 6 blind agents | **Not done.** |
| 5. Unblind, analyze, report | **Not done.** |

Nothing in this folder is committed yet.

## What's here

| Path | What it is |
|---|---|
| `scenarios/s1…s6/` | `fixture/` (starting repo), `request.txt` (turn 1), `followup.txt` (turn 2, the same for both arms), `ground_truth.md`, `check.py`, `reference/` (a correct fix), `naive/` (the literal request, for symptom scenarios only). `scenarios/INDEX.md` is the summary. |
| `run_one.sh <s> <skill\|base> <rep>` | Runs one two-turn session in a fresh git copy of the fixture, writing to `runs/<s>_<arm>_<rep>/`. The skill arm prefixes `/why-chain` and loads the plugin with `--plugin-dir`; the baseline sends the bare request. Both arms get the same tool allowlist under `--permission-mode dontAsk`, with pip, crontab, brew, curl, `git push` and web access denied. |
| `jobs.txt` | The 36 jobs. Run all of them with `xargs -P 12 -L 1 ./run_one.sh < jobs.txt`. |
| `runtrace.py` | Turns a stream-json transcript into a readable trace (`python3 runtrace.py <turn.jsonl>`), or prints cost/turns/time (`--metrics`). |
| `score_and_blind.py` | Runs every checker, then writes `results.json` (unblinded), `blind_key.json` (id → run) and `graders/<s>/<s>-A…F.md` (blinded packets: run-folder names and `/why-chain` are scrubbed out). |
| `grader_prompt.md` | The grader brief. Fill in `{GT}`, `{RUNS}` and `{OUT}` per scenario. It doesn't mention the skill, says format must not affect scores, and asks for 5 scores (1–5) plus a ranking of the six. |
| `checker-src/`, `validation/` | The checkers' sources (`check.py` = `common.py` + `sN.py`) and extra validation variants. To rebuild them, run `python3 checker-src/validate.py <dir>`. |

Each run folder holds:
- `turn1.jsonl` and `turn2.jsonl`: the full transcripts;
- `after_turn1.txt`: whether the repo had already changed before the user replied;
- `final.diff`, `wall.json`, and the final `repo/`.

## Scenarios

| id | type | request → truth |
|---|---|---|
| s1 | request is right | Switch the CSV export to the `csv` module. That is the fix. |
| s2 | symptom | "Retry the flaky test." The real cause is that tied tags are ordered by set iteration, which depends on the hash seed. A retry inside the same process can't help. |
| s3 | request is right | Env-var overrides for every setting. The traps are type conversion and a missing ini file. |
| s4 | wrong stated cause | The user blames rounding, but amounts are already exact `Decimal`. Orders are grouped by UTC date instead of the store's local date. |
| s5 | request is right, tempting to over-build | 3-attempt backoff retries. Queues, async or new dependencies count as over-reach. |
| s6 | symptom | "LRU cache on search()." The catalog is re-read on every query, queries are distinct, and the file changes while the service runs. |

## Next steps

1. **Score and blind:**
   ```bash
   /Users/oat/venv/bin/python3 score_and_blind.py
   ```
   - Use the venv Python, because the checkers need pytest.
   - Score sequentially. The s6 checker is timing-based; it held with 3 copies in parallel, but don't push it harder than that.
2. **Grade:** spawn 6 independent agents, one per scenario. Give each the grader brief with `{GT}` = `scenarios/<s>/ground_truth.md`, `{RUNS}` = the six files in `graders/<s>/`, and `{OUT}` = `graders/<s>/grades.json`.
   - Don't give a grader the key, `results.json`, or the skill.
   - Don't grade them yourself. Whoever built the skill is biased.
3. **Unblind and report.** Map the IDs back with `blind_key.json`, then report **per scenario** (n=3 per arm), not one overall win rate. Keep two sources apart:
   - **from the checker scripts:** pass/score of the final repo;
   - **from LLM graders:** the five process scores and the rank.

   Add rows for:
   - overhead: cost, turns and wall time per arm;
   - harm on the three request-is-right controls (s1, s3, s5): invented depth, over-reach, or friction before doing a clear task.
4. **Optional:** if the skill loses or causes harm on the controls, change the skill and rerun only the affected scenarios.

## If runs/ is missing

The runs were made in a scratchpad. A background job was set to copy them here once all 36 finished. If `runs/` is missing or has fewer than 36 folders, rerun them all:

```bash
cd productivity/why-chain/evals && xargs -P 12 -L 1 ./run_one.sh < jobs.txt > runs.log 2>&1
```

This is what the first batch cost: per run, $0.31–1.73 (median about $1) and 1.5–2.5 minutes. The full set of 36 took about 25 minutes, 12 at a time, and cost about $35.

## Caveats

- **Blinding isn't perfect.** Skill-arm replies use the `Request:/Root:/Test:` template, so a grader can probably guess the arm. The grader brief says format must not count, and the checker scores can't see format at all.
- **Both arms load the user's global `~/.claude/CLAUDE.md`.** It says to work without checking in and to commit at checkpoints, so expect the baseline to build and commit in turn 1. That's the real counterfactual, not a flaw.
- **Env-prefixed commands may be denied.** A command like `TZ=… python3` may not match the allowlist; `env TZ=… python3` is allowed. Check the `denials` count in `results.json` for skew between arms.
- **The follow-up gives context, not the diagnosis.** Some of it still points toward the cause, for example s4's "monthly totals usually line up". Both arms get the same text.
- **Packaging:** `evals/` sits inside the plugin folder, so it would ship with the plugin. Before committing, decide whether to keep it there or move it. `.gitignore` already excludes `runs/`, `graders/` and the result files.
