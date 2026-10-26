# why-chain eval: handoff

Updated 2026-10-26 (third session). v1, v2 and v3 are finished. **v3: generalisation holds on all pre-registered criteria.** Full results so far are in `RESULTS.md`.

## Where it stands

| Round | Skill wins | Turn-1 builds on controls (s1, s3, s5) | Turn-1 builds on symptoms (s2, s4, s6) | Checker passes |
|---|---|---|---|---|
| v1 | 2 of 6 (s1, s6) | 0/9 | 0/9 | 17/18 |
| v2 | 4 of 6 (s1, s3, s5, s6) | 9/9 | 0/9 | 18/18 |
| v3 | 4 of 5 (s7, s8, s10, s11) | 6/6 (s7, s8) | 0/9 (s9, s10, s11) | 14/15 |

v2 was tuned by someone who had seen s1–s6, so it shows the fix took, not that it generalises. v3 is the generalisation test.

## Done this session (2026-10-26)

1. **v3 was run:** 30 runs, 0 denials, 0 errors, about $18. The data is archived in `v3/` (gitignored), with tables in `v3/analysis.md`. Results and the verdict are at the end of `RESULTS.md`.
2. **The verdict:** generalisation holds on all pre-registered criteria, but two of them pass only at their threshold.
3. **The graders were swapped.** v3 was graded by `opencode/deepseek-v4.1-flash-free`, at the owner's request ("cheap subagents"), instead of Claude `general-purpose` agents.
   - **Don't compare v3 ranks one to one with v1/v2.**
   - Grader isolation was checked: each opened only its 7 files, and all 7 of them.
   - No SKILL.md text leaked into the packets.
4. **The earlier setup work is in commits `afb4438` and `47e64c8`:** the harness fix, the criteria and s7–s11.

5. **v3 was re-graded with Claude `general-purpose` graders** (`v3-claude/`). The skill wins 5 of 5, and s9 flips to the skill. The ranks are now comparable with v1/v2.

6. **v4 was run:** 3 fresh scenarios (s12–s14), Sonnet and opencode deepseek as builders, with and without the skill, 2 reps each, graded by cheap graders. The skill helps Sonnet on all criteria. Transfer to deepseek misses by one checker run (s13). The details are at the end of `RESULTS.md`. The harness is `run_one_oc.sh` (opencode) plus `CLAUDE_MODEL=sonnet run_one.sh`.

## Next step

Nothing is required. Options:
- **The s4 owner decision**, now with evidence from s9 and s11 (see "Notes" in `RESULTS.md`).
- **Rerun s1–s6 on the fixed harness** (about $36).

## Still open

- **s4 decision (owner):** should the skill build a *different* fix without asking when the evidence is strong? Under Claude grading, acting on a different fix without asking was penalised in both s9 and s11. Only the flash grader rewarded it in s9.
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

- **opencode from a background shell hangs forever** unless stdin is `/dev/null`: `opencode run` waits for piped input. `run_one_oc.sh` handles this. Use `--standalone` plus a throwaway HOME, or the user's global CLAUDE.md and skills leak into the run.

- **Runs inside this repo** get every Edit and Write refused under headless `dontAsk`. Always use a scratch folder.
- **`score_and_blind.py` overwrites** `results.json`, `blind_key.json` and `graders/`, and `run_one.sh` deletes run folders with the same name. Archive the previous round first.
- **If `allow_bash_hook.py` can't be found,** every Bash call is denied silently and the agents blame "a broken hook". The script now resolves the hook's path before it changes directory.
