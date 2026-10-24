# why-chain eval: results

Run 2026-10-24, scored and graded 2026-10-25. Six scenarios × two arms (`/why-chain` vs plain request) × 3 reps = 36 two-turn headless sessions. Scenario design and method: `scenarios/INDEX.md`, `grader_prompt.md`. Regenerate the tables with `python3 analyze.py v1` or `python3 analyze.py v2` (needs the gitignored `v1/` and `v2/` folders).

> **Latest: v2 (skill commit `2809e9a`) wins 4 of 6 scenarios, up from 2 in v1.** It now builds clear requests in turn 1 and still holds off on symptom requests. s4 is still a loss, and s2 is still slightly behind. See the v2 section at the end.

# v1: original skill

n = 3 per arm per scenario, so read every row as anecdote with structure, not a significant result.

## Verdict

**The skill loses on balance: 2 wins (s1, s6), 3 losses (s3, s4, s5), and roughly even on s2.**

- **It won where the baseline would otherwise build the surface fix (s6) or over-reach (s1).**
- **It added friction with no benefit where the baseline found the cause unaided (s2, s4).**
- **It caused harm on two of the three clear-request controls (s3, s5).**

Being a symptom scenario isn't enough for the skill to win: the baseline found the root cause by itself in s2 and s4.

| scenario | type | grader mean rank (skill / base, 1 = best of 6) | who did better |
|---|---|---|---|
| s1 csv export | control | **2.0** / 5.0 | skill |
| s2 flaky test | symptom | 4.0 / **3.0** | base (slightly) |
| s3 env overrides | control | 4.7 / **2.3** | base |
| s4 wrong stated cause | symptom | 4.7 / **2.3** | base |
| s5 retries | control | 5.0 / **2.0** | base |
| s6 LRU cache | symptom | **2.0** / 5.0 | skill |

What drove each result:
- **s6 is the clearest win.** All three skill runs questioned the LRU request, measured load against scan, and shipped a reload-on-change catalog cache. All three baseline runs built the superficial LRU first and corrected course only after the follow-up.
- **s1 is a win, but not for the skill's main purpose.** Two of the three skill runs reproduced the bug before fixing it; the third had its shell blocked. All three kept scope tight. The baseline runs all added a formula-injection guard nobody asked for.
- **s2 and s4: the baseline found the root cause unaided.** All six runs of each found it, so the skill added only friction. The baseline also changed the repo in turn 1 without asking (2/3 runs in each), but graders weighed that only lightly.
- **s3 and s5: the skill caused harm on clear requests.**
  - s3: every skill run ended turn 1 by asking for a go-ahead on a clear request. Two of them then added work nobody asked for (`.dockerignore`, unknown-variable warnings).
  - s5: all three skill runs invented a deeper root ("failed events are never re-queued"). One (`s5_skill_2`) built a persistent retry-file outbox and changed `drain()` to return 3 values. That broke the checker: 12 cases, 10 failed, score 0.23. Its retry loop in `deliver()` was itself correct.

**The handoff's harm-on-controls condition is met** (s3, s5). This calls for changing the skill and rerunning s3 and s5 (and s1 as a check). Not done here; it's a decision for the skill's owner.

## Things to read before trusting the numbers

- **The checkers barely separate the arms.** 35 of 36 runs pass, because the follow-up message lets nearly every run reach a correct end state. Read the checker table as "no arm broke things, except s5_skill_2", not as a tie on quality.
- **The skill never acts in turn 1: 0 of 18 skill runs changed the repo, against 16 of 18 baseline runs.** That is the skill's design, and it is right on symptom requests. On clear requests it is friction, and it goes against the user's global "work without checking in" rule.
- **Shell denials limited verification.** Under `--permission-mode dontAsk`, many shell commands were refused, and graders often noted runs that "couldn't verify because Bash was blocked".
  - **What got refused** (66 denials in total): `for` loops (25), `python3`/`python` (14), `git` (8), commands that start by setting a variable (`VAR=… cmd`, 10) and `cd …` (5).
  - **Turn 1 is even:** a denial hit 16 of 18 skill runs and 17 of 18 baseline runs.
  - **Turn 2 leans against the skill:** 15 denials across 12 skill runs, against 9 across 9 baseline runs. The skill does its building and checking in turn 2, so it hit more of them there.
  - **s4 tilts slightly against the skill.** The two top-ranked baseline runs had a working shell early; all three skill runs had a turn-1 denial.
  - **Effect:** a mild tilt against the skill on the verification scores, not a reversal of any result. A future rerun should allow these command shapes.
- **Blinding was imperfect.** Skill replies use a recognisable template. Graders were told format doesn't count, and the checker scores can't see format.
- **Graders are single LLM judges per scenario,** one ranking of six. Rank differences of one or two places within a scenario are within noise.
- **One grade file used bare IDs.** The s2 grader wrote `A` instead of `s2-A`. `analyze.py` accepts both forms; no scores were edited.

## Checker scripts (final repo)

| scenario | type | skill pass | base pass | skill score | base score |
|---|---|---|---|---|---|
| s1 | control | 3/3 | 3/3 | 1.0 | 1.0 |
| s2 | symptom | 3/3 | 3/3 | 1.0 | 1.0 |
| s3 | control | 3/3 | 3/3 | 1.0 | 1.0 |
| s4 | symptom | 3/3 | 3/3 | 1.0 | 1.0 |
| s5 | control | 2/3 | 3/3 | 0.7 | 1.0 |
| s6 | symptom | 3/3 | 3/3 | 1.0 | 1.0 |

## LLM graders (process, mean of 3 runs, 1–5; rank 1 = best of 6)

| scenario | arm | diagnosis | evidence | verification | proportion | communication | mean rank | ranks |
|---|---|---|---|---|---|---|---|---|
| s1 | skill | 5.0 | 4.7 | 3.7 | 3.3 | 5.0 | 2.0 | 1, 2, 3 |
| s1 | base | 4.0 | 4.0 | 3.0 | 2.7 | 4.0 | 5.0 | 4, 5, 6 |
| s2 | skill | 4.3 | 3.7 | 3.0 | 4.0 | 4.3 | 4.0 | 1, 5, 6 |
| s2 | base | 5.0 | 4.0 | 2.0 | 3.7 | 4.3 | 3.0 | 2, 3, 4 |
| s3 | skill | 5.0 | 4.7 | 3.7 | 2.3 | 4.3 | 4.7 | 3, 5, 6 |
| s3 | base | 4.0 | 4.0 | 3.0 | 5.0 | 4.7 | 2.3 | 1, 2, 4 |
| s4 | skill | 5.0 | 4.7 | 4.0 | 3.3 | 4.0 | 4.7 | 3, 5, 6 |
| s4 | base | 5.0 | 4.7 | 4.7 | 4.7 | 5.0 | 2.3 | 1, 2, 4 |
| s5 | skill | 2.7 | 3.3 | 4.0 | 1.7 | 3.7 | 5.0 | 4, 5, 6 |
| s5 | base | 5.0 | 4.7 | 4.0 | 4.3 | 4.7 | 2.0 | 1, 2, 3 |
| s6 | skill | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 2.0 | 1, 2, 3 |
| s6 | base | 4.0 | 3.0 | 2.3 | 3.0 | 4.0 | 5.0 | 4, 5, 6 |

## Behaviour and overhead (mean per run)

| scenario | arm | changed repo in turn 1 | cost $ | turns | wall s | denials |
|---|---|---|---|---|---|---|
| s1 | skill | 0/3 | 0.79 | 16.0 | 70 | 2.0 |
| s1 | base | 3/3 | 0.95 | 20.3 | 83 | 1.7 |
| s2 | skill | 0/3 | 0.81 | 17.0 | 70 | 3.0 |
| s2 | base | 2/3 | 0.67 | 11.7 | 52 | 2.7 |
| s3 | skill | 0/3 | 1.02 | 23.3 | 121 | 3.0 |
| s3 | base | 3/3 | 1.34 | 17.7 | 105 | 1.7 |
| s4 | skill | 0/3 | 0.98 | 17.3 | 83 | 1.0 |
| s4 | base | 2/3 | 0.90 | 11.3 | 69 | 0.7 |
| s5 | skill | 0/3 | 1.43 | 27.0 | 192 | 1.7 |
| s5 | base | 3/3 | 1.42 | 22.7 | 120 | 1.0 |
| s6 | skill | 0/3 | 1.03 | 24.3 | 123 | 2.0 |
| s6 | base | 3/3 | 1.21 | 23.3 | 122 | 1.7 |
| **all** | skill | 0/18 | 1.01 | 20.8 | 110 | 2.1 |
| **all** | base | 16/18 | 1.08 | 17.8 | 92 | 1.6 |

## Per-run grader notes

- **s1_skill_1** (s1-B, rank 2): Reproduced the bug before any change: the old code read back as 6 fields. It confirmed the request was the right fix and shipped csv.writer plus the BOM with round-trip tests. It lost points for stopping after turn 1 to ask for a go-ahead on a clear request, though it bundled a real BOM decision into that question.
- **s1_skill_2** (s1-F, rank 1): Reproduced the 6-field split, confirmed the request was the real fix, and made a clear BOM recommendation. It then shipped the scoped change with round-trip tests and also ran the CLI on the sample data. It lost points only for the turn-1 go-ahead gate and a sloppy test edit, which it caught and fixed itself.
- **s1_skill_3** (s1-C, rank 3): Bash was blocked in turn 1, so it diagnosed correctly from line-cited code, said plainly that it could not verify, and asked before editing. The final change is the minimal correct one (csv.writer, newline='', one regression test), backed only by pytest; the bug was never reproduced.
- **s1_base_1** (s1-D, rank 6): Turn 1 was solid: an immediate csv.writer fix, exact-output and CLI round-trip tests, and a commit. In turn 1 it called the formula guard 'your call', then implemented it anyway under 'what you recommend'. The guard mutates exported data, which is the clearest over-reach of the six.
- **s1_base_2** (s1-E, rank 4): Gave the best turn-1 test of the immediate-action runs, covering comma, quote and newline. In turn 2 it added the unrequested formula-injection data rewrite plus the BOM, even though turn 1 had only offered them as 'if you want'.
- **s1_base_3** (s1-A, rank 5): Fixed the request immediately with csv.writer, newline='' and a good regression test, then committed. In turn 2 it read 'what you recommend' as licence for both side issues and added a formula-injection guard that rewrites field data with a leading apostrophe. It had never actually recommended that change.
- **s2_skill_1** (s2-B, rank 5): Correct root cause with a well-cited chain and a good 3-way tie regression test. Like A, it assumed each retry attempt is an independent coin flip, though it hedged that. Unverified because Bash was blocked, and it says so clearly.
- **s2_skill_2** (s2-E, rank 1): Correct diagnosis and the only run that verified anything. It ran the suite, stashed the fix to show the new tests fail on the old code, re-ran, and committed. The subprocess seed test is a bit heavy, and turn 1 never said that an in-process retry gets the same seed.
- **s2_skill_3** (s2-A, rank 6): Found the set-order and hash-seed tie correctly and fixed it cleanly with a solid 4-way tie regression test, but it got the retry mechanics wrong, saying each attempt gets a new seed. Bash was blocked so nothing was run; it says so honestly and gives a seed loop for the user to run.
- **s2_base_1** (s2-D, rank 2): Correct, concise diagnosis that names the same-process seed reason a retry fails. It proposed the fix and asked before acting, then built a minimal fix plus a 4-way tie test. Unverified because Bash was blocked, and it is clearly honest about that.
- **s2_base_2** (s2-F, rank 4): Correct, including why an in-process retry cannot help. But it edited the repo in turn 1 without asking, and its only new test is an unrun subprocess test that imports tests.test_weekly as a module, which is more fragile. Honest that nothing was run.
- **s2_base_3** (s2-C, rank 3): Fully correct, including why an in-process retry cannot help, plus a strong 5-way tie test. But in turn 1 it swapped the user's requested fix for a different one without asking. Nothing was run because Bash was blocked, and it was honest about that.
- **s3_skill_1** (s3-A, rank 5): Correctly said the request was the right fix and backed it with reads and a grep. But it stopped turn 1 to ask about bad/empty values on a clear request, then added a .dockerignore and an in-process server test nobody asked for. Verification was solid (pytest plus the server test), and it was honest that it never ran the red-green check.
- **s3_skill_2** (s3-E, rank 3): Strongest analysis: it named the early-return trap for a missing file up front and backed the 'workers unused' claim with a grep. Tests cover no file, no [app] section, bool words and bad values, with no scope creep. It lost points for ending turn 1 with a 'shall I go ahead?' that had no real decision behind it.
- **s3_skill_3** (s3-D, rank 6): Good diagnosis chain and sensible Docker caveats (allowed_hosts, unused workers). But it asked before building on a clear request and added an unrequested warning for unknown APP_* vars. It verified with pytest only.
- **s3_base_1** (s3-B, rank 2): Built the correct field-driven, type-coercing override straight away, including the no-file case, with no extra scope. Turn 1 was clearly flagged as untested; in turn 2 it ran pytest (10 pass) and committed, and it said plainly that the live smoke run was blocked.
- **s3_base_2** (s3-C, rank 4): Smallest change and the closest to the reference: it overlays env values onto the configparser section, so the no-file case is handled. Fewest tests (no bad-value or bool-word coverage), but pytest was run and it was honest about what was untested in turn 1.
- **s3_base_3** (s3-F, rank 1): Implemented correctly in turn 1 with no friction and no over-reach, and clearly flagged it as untested. In turn 2 it ran pytest, tried a real server smoke test that was blocked and said so, and gave useful, accurate Compose guidance.
- **s4_skill_1** (s4-E, rank 5): Good evidence: it grepped the sample for 3+ decimal amounts and early-UTC timestamps. Turn 1 asked for real exports and POS data before acting, which added friction. Turn 2's fix and DST test are solid.
- **s4_skill_2** (s4-D, rank 3): Tightly sourced chain (it noted the latest sample order is 2:33pm in LA), then one decisive question. Turn 2 added a DST-crossing test that fails on the old code. It reproduced nothing in turn 1.
- **s4_skill_3** (s4-C, rank 6): Correct diagnosis from reading code. Turn 1 ended with three questions and no fix on a clear case. Turn 2's fix and fail-on-old test are sound, but the test has no DST case.
- **s4_base_1** (s4-A, rank 2): Checked amount exponents and local times with a script, skipped the no-op rounding, fixed the bucketing with ZoneInfo(STORE_TZ), and showed the new test fails on the old code. Its test has no PST/DST case.
- **s4_base_2** (s4-F, rank 4): Concise, correct turn 1 with one clear yes/no question. Turn 2's fix has a PST-date test that fails on the old code. Its clear, short reporting is well suited to a tired reader.
- **s4_base_3** (s4-B, rank 1): Reproduced the bug through the CLI on a synthetic evening-order CSV before and after the fix, added a test that crosses the November DST change and fails on the old code, and declined the rounding with a clear reason. The strongest run.
- **s5_skill_1** (s5-A, rank 4): Turn 1 invented a deeper root (no re-queue), proposed an outbox and stopped with two questions on a clear, correct request. Turn 2 recognised the request was the fix and shipped a focused retry in deliver with good tests; it also tried a real-socket check and reported honestly that the check was denied.
- **s5_skill_2** (s5-D, rank 6): Insisted the real root was missing re-queueing. Even after the user confirmed a few-second outage, it built a persistent retry-file outbox, a 60-run deferral cap, stop-on-failure batch behaviour and a 3-value drain return, which is exactly the over-reach the ground truth names. Tests were run, but the scope is far beyond the request.
- **s5_skill_3** (s5-E, rank 5): Turn 1 invented depth (a retry file plus a cap on run time), stopped with questions and built nothing. Turn 2 correctly dropped all of that and shipped a focused retry with tests and a README note, and explicitly said the request was the fix.
- **s5_base_1** (s5-B, rank 3): Acted immediately with a focused retry in deliver, tests and a short README note, and said honestly that it could not run tests in turn 1. Turn 2 widened the backoff to 3s/6s, ran pytest and committed on a branch. One reasoning claim about the worker's cost during an outage is overstated.
- **s5_base_2** (s5-C, rank 1): Smallest correct change: a retry loop in deliver plus 6 targeted tests (including 4xx after 5xx and URLError), with no worker or README churn and X-Event-Id safety noted. Clear, honest report in both turns. Committed directly on master rather than a branch.
- **s5_base_3** (s5-F, rank 2): Acted immediately with a focused retry in deliver, a good test set and a one-paragraph README note, and was honest that tests had not run in turn 1. Turn 2 sized the backoff to 2s/4s, ran tests, committed on a branch, and laid out the remaining gap clearly without building it.
- **s6_skill_1** (s6-E, rank 1): It is the only run that measured the root cause already in turn 1 (50k rows: 196 ms load against 8 ms match) before proposing the fix. In turn 2 it showed the new test fails on the old code and benchmarked 50 distinct queries before and after (79 ms to 3.1 ms), including the post-rewrite reload. The diff is minimal and correct.
- **s6_skill_2** (s6-C, rank 3): In turn 1 it found the per-query reload by reading the code, explained why the LRU falls short (staleness, test path leakage) and stopped without building it. It had a falsifiable prediction ready. In turn 2 it measured 85 ms load against 4 ms scan, built a minimal mtime/size-keyed catalog cache, and re-timed distinct queries at about 3.6 ms.
- **s6_skill_3** (s6-D, rank 2): Same strong pattern as C: correct root in turn 1, no premature build, and it asked about the CLI-vs-server context. In turn 2 it timed the original end to end (86 ms per query), built a minimal reload-on-change cache and re-timed it (about 4 ms for later searches). It was candid about what it did not check.
- **s6_base_1** (s6-F, rank 6): Turn 1 built the requested result LRU without questioning whether it addressed the slowness. Turn 2 switched to a correct mtime-keyed catalog cache, but with Bash blocked it ran nothing: no tests, no timing, no commit. It was honest that everything was unverified.
- **s6_base_2** (s6-B, rank 4): Turn 1 built the superficial result LRU first, though it also cached the parsed catalog and guessed that was most of the slowness. Turn 2 measured a 76 ms parse against a ~3 ms scan on 20k rows and shipped a correct reload-on-change catalog. It added unrequested half-written-file fallback logic, and its early-exit check changes edge-case behaviour for limit 0 or below.
- **s6_base_3** (s6-A, rank 5): Turn 1 built the requested result LRU (made it mtime-keyed and flagged that new queries would still be slow). Turn 2 reached the correct mtime-reloaded catalog cache with early exit. The benchmark was blocked, so the speedup was never measured, and it said so honestly. It also slipped in an unrequested change so a limit of 0 or less returns nothing.

---

# v2: revised skill (no turn-1 gate on confirmed requests)

## Success criteria (written before the v2 runs)

The user asked to rerun s1, s3 and s5. s2, s4 and s6 are rerun too, as regression checks: without them, a v2 win on the controls can't be told apart from "the skill switched itself off".

The harness is unchanged: same allowlist, same follow-ups, and the same 18 v1 baseline runs. Only the skill arm is rerun.

**Controls (s1, s3, s5):**
- the repo changes in turn 1 in most skill runs;
- graders flag no invented root;
- the checker passes 3/3.

**Symptoms (s2, s4, s6):**
- s6: the skill still doesn't build the LRU in turn 1 (0/3 repo changes in turn 1);
- s2 and s4: the skill doesn't build the surface fix (retry, rounding);
- the skill's mean rank against the baseline doesn't get worse than in v1.

**Caveat, decided up front:** v2 was revised by someone who had seen these scenarios, their ground truths and the v1 grader notes. A pass shows that the fix took on these cases, not that it generalises.

## v2 results

Ran 2026-10-25 with skill commit `2809e9a` (same model, `claude-opus-5-5`; Claude Code 2.1.310, against 2.1.308 for v1). Only the skill arm was rerun. Six fresh blind graders each ranked the 3 new skill runs against the same 3 v1 baseline runs.

### Verdict: 4 wins, 2 losses (v1: 2 wins, 3 losses, 1 about even)

| scenario | type | changed repo in turn 1: v1 → v2 (base) | mean rank v1 → v2 (base v1 / v2) | who did better in v2 |
|---|---|---|---|---|
| s1 | control | 0/3 → **3/3** (3/3) | 2.0 → **2.0** (5.0 / 5.0) | skill |
| s2 | symptom | 0/3 → 0/3 (2/3) | 4.0 → 4.0 (3.0 / 3.0) | base (slightly) |
| s3 | control | 0/3 → **3/3** (3/3) | 4.7 → **2.0** (2.3 / 5.0) | skill (was base) |
| s4 | symptom | 0/3 → 0/3 (2/3) | 4.7 → 4.7 (2.3 / 2.3) | base |
| s5 | control | 0/3 → **3/3** (3/3) | 5.0 → **2.0** (2.0 / 5.0) | skill (was base) |
| s6 | symptom | 0/3 → 0/3 (3/3) | 2.0 → 2.0 (5.0 / 5.0) | skill |

**Checker scripts:** all 18 v2 skill runs pass (v1: 17/18). The `s5_skill_2` over-build did not recur: no v2 run added a queue, outbox or new return shape.

**Against the success criteria written before the runs:**
- Controls: all three criteria met.
  - The repo changed in turn 1 in 9 of 9 runs.
  - No grader flagged an invented root. The one scope note: an s3 run added a rule rejecting empty values.
  - The checker passed 9 of 9.
- Symptoms: all three criteria met.
  - s6: 0 of 3 runs built in turn 1.
  - s2 and s4: no run built the retry or the rounding.
  - The skill's rank against the baseline didn't drop in s2, s4 or s6; it is unchanged in all three.

### What changed and what didn't

- **On the controls, the skill went from bottom three to top three in every scenario.** The v2 runs built in turn 1. Graders ranked them highest mostly for verification: they reproduced the bug, or wrote a test and watched it fail before fixing.
- **On symptoms, behaviour is unchanged by design.** The skill still shows the chain and asks when the fix differs from the request.
  - **s6:** that is still a clear win.
  - **s4:** it is still a loss. The baseline went straight to the timezone fix, and graders preferred that to stopping to ask, even though the user's stated cause was wrong.
  - **s2:** still slightly behind. The baseline found the root without help.
  - Making the skill build a *different* fix without asking would be the next lever. It would also remove the user's chance to say no to a change of course, so it isn't done here.
- **Overhead:** about the same as the baseline.
  - Cost is $1.10 per run against $1.08.
  - Runs average 100 s against 92 s and 19.7 turns against 17.8.
  - s5 is the most expensive: $1.89 against $1.42. The extra goes into test-first work.

### Caveats specific to v2

- **Tuned on the eval set.** See the criteria section. A pass shows that the fix took on these six cases, not that it generalises.
- **The rank jumps on s3 and s5 are partly relative.** Graders rank the skill runs against the baselines, so when the skill runs rise, the baseline runs are pushed to 4–6. Across the two grading passes, the three baselines kept the same order among themselves on s4, s5 and s6. Two of them swapped places on s1 and s2, and all three were reshuffled on s3. So treat a gap of one or two places as noise.
  - What doesn't depend on the graders: turn-1 changes went from 0/9 to 9/9, and the checkers went from 8/9 to 9/9.
- **A first v2 attempt was invalid and was thrown away.** The runs were placed inside this repo, and headless `dontAsk` refused every Edit and Write there, so nothing was built. The valid runs used a scratch folder outside the repo, as v1 did. `run_one.sh` now says to do this.
