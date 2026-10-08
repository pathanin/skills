# worktree-swarm evals

How to run the `worktree-swarm` eval suite, what each check measures, and the recorded results.

## What the suite tests

Four cases. Each scaffolds a small stdlib-Python git repo with a `check.sh` acceptance script; the prompt tells the agent to finish with `./check.sh > check-output.txt`. Every case pins the integrator to Opus (`model: opus` in its `prompt.md`), so the builder, scout and verifier models are the skill's choice, not the session's. Don't pass `--model`, because it overrides that pin.

| Case | Setup | Right outcome |
|---|---|---|
| `fanout-six` | `unitconv` needs six unit modules behind a pinned `registry.py` contract. Tests and spec exist. | 6-7 worktree builders on haiku with complete briefs, one read-only Opus low-effort verifier per branch, all 20 tests pass, `registry.py` and tests untouched, no worktree or agent branch left. Old skill capped at 4 pieces, so this is the ceiling check. |
| `two-piece` | Username validation on the server plus its client message. The prompt leaves the error code's name open. | 2-3 worktree builders on haiku, the code pinned in both briefs, at least 3 agents in total (verifiers make up the floor; no padded third piece), all tests pass. |
| `judgment-piece` | Three mechanical modules from `SPEC.md`, plus "totals are sometimes a cent low, nobody knows why". | Mechanical pieces on haiku; the debugging piece on sonnet or opus unless the brief already names the root cause; one Opus low-effort verifier per branch; all 8 tests pass, and the reply names the real cause (`int()` truncating `float * 100`). |
| `no-swarm` | A one-line off-by-one in `paginate`. The prompt doesn't mention swarming. | Fixed directly, with no worktree agents. Should-not-fire case. |

### How the checks measure

- **Outcome checks** read `check-output.txt`, which `check.sh` writes by running the suite and git itself. An agent could hand-write that file, so when a pass looks surprising, rerun `./check.sh` in the run's `repo`:
  - `tests-pass`: `CHECK RESULT: PASS (N tests)` with N at least the fixture's test count, so deleting tests fails it.
  - `contract-intact`: `sha256sum -c` over the files the task must not change (the registry contract, the tests, the spec).
  - `cleaned-up`: `git worktree list` and `git branch --list 'worktree-*' '*agent*' 'swarm/*'` both empty.
- **Swarm-shape checks** are `tool_used` graders on the integrator's top-level tool calls. `input_match` is a JS-compatible regex (no flags, no apostrophes) tested against each call's input as compact JSON, so lookaheads pick out fields regardless of key order:
  - `builders-haiku` / `mechanical-on-haiku`: worktree builders on `haiku`, with an exact count (6-7 in `fanout-six`, 3+ in `judgment-piece`, 2+ in `two-piece`).
  - `builder-briefs-complete`: **every** builder brief (min = builder count) has the git-stash rule, the `BRANCH:` / `CHECK:` hand-back format, a stop rule ("report the gap" / "do not improvise"), a file-ownership line, and a concrete done-check command (`unittest`, `pytest` or `python3 -c`).
  - `verifier-briefs-complete`: **every** builder has a verifier (min = builder count) on `opus` at `effort: low`, without isolation, read-only, covering exactly one `agent-<id>` branch, with `diff`, a done-check command, and a PASS/FAIL verdict.
  - `no-other-verifier-model`: no verifier-shaped call (non-worktree, prompt says `git ... diff`) on another model or effort.
  - `every-agent-has-model`: no `Agent` call omits `model`.
  - `ledger-kept`: a `Bash` or `Write` call writes a `ledger.md`-style file. `tool: Bash|Write` is a `run.py` extension; the harness only takes one tool name.
  - `merge-base-checked`: the integrator ran `git merge-base` before porting a branch.
  - `debugging-brief-fits-model` (judgment-piece): the totals builder is on sonnet or opus, or on haiku with the root cause already in its brief.
  - `floor-three-agents`, `two-builders`, `code-pinned-in-both-briefs` (two-piece): the 3-agent floor without a padded third builder, and the error code in both builder briefs.
  - `no-worktree-agents`, `skill-not-invoked` (no-swarm): no swarm and no skill load on a one-line fix.
- **LLM checks** only grade the reply: `reports-models` (fanout-six) and `relays-root-cause` (judgment-piece).

The outcome checks guard correctness, and the swarm-shape checks separate the arms. A check that a baseline would pass only because it launches no verifiers was dropped (`one-branch-per-verifier`; its condition lives inside `verifier-briefs-complete`).

Every `tool_used` grader sets `arm: both`, so it counts in the no-skill baseline too and the delta measures the skill.

## Why there's a custom runner

`claude plugin eval` refuses `isolation: "worktree"` inside its harness ("worktree isolation is unavailable in this session (plugin evaluation harness)"), and worktree isolation is the mechanism this skill exists to drive. So `run.py` runs each case with a plain `claude -p` session instead. It reads the same case files (`fixture.sh`, `prompt.md`, `graders/*.md`) and grades them the same way as the harness:

- **`tool_used`** counts top-level `Agent` calls whose input (as compact JSON) matches `input_match`. Calls whose result was an error, such as a refused worktree, don't count.
- **`regex`** reads `pattern` against the reply or a file.
- **`llm`** asks a judge model (default sonnet) three times and takes the majority.

The directory layout still matches `claude plugin eval`, so the suite can move back to it if the harness ever allows worktrees.

The first harness pilot also exposed a gap in the skill. When isolation was refused, the integrator relaunched all six builders into the shared checkout. `SKILL.md` now says to create the worktrees by hand in that case.

## Before you run

1. Claude Code installed and logged in (`claude --version`).
2. Nothing named `worktree-swarm` installed as a plugin (`claude plugin list`), or the without-skill arm isn't a baseline.
3. Each run executes `fixture.sh` and an unsandboxed `claude -p` with `Bash`, `Edit` and `Write` allowed and `--permission-mode acceptEdits`, in a fresh temp repo. Run it only on a machine where that is acceptable, such as a cloud container.

## Run it

From the skill directory:

```bash
cd internal-tools/worktree-swarm
python3 evals/run.py --runs 3 -j 2            # all cases, with and without the skill
python3 evals/run.py --case fanout-six --runs 1 --arms with   # one pilot run
```

- `--arms with,without` (default) runs every case with `--plugin-dir` pointing at this skill and without it. The difference is the skill's effect.
- `-j` sets how many sessions run at once. Each swarm run starts up to a dozen subagents of its own, so keep it at 2-3 to stay under rate limits.
- Output goes to `evals/results/<timestamp>/` (gitignored): `summary.md` (pass counts per check and arm, mean score, cost), `summary.json`, and per run `trace.jsonl`, `result.json` (verdicts, the `Agent` calls with model/effort/isolation, the reply), and a `repo` symlink to the run's temp repo.

## Read the result

Start with `summary.md`. When a swarm-shape check fails, open that run's `result.json`: its `agents` list shows every top-level `Agent` call with `model`, `effort`, `isolation`, `subagent_type`, and whether the call errored. The full record is `trace.jsonl` next to it.

Before changing the skill, decide which of these a red is:

- **The skill is wrong:** the integrator really did the wrong thing (a builder without a model, a verifier on haiku). Fix `SKILL.md`.
- **The grader is wrong:** the swarm did the right thing in a shape the regex didn't expect (for example a verifier brief that never says `diff`). Fix the file in `graders/`.
- **The environment is wrong:** rate limits, a timeout, or a refused tool. Look at `stderr.txt` and the `error` flags in `agents`, then rerun.

## Results

### 2026-10-08: second full run, stricter graders

Same setup as the first run, with the current `SKILL.md` (one Opus verifier per branch) and the stricter graders above. 24 runs, $15.31 agent cost. Every `check-output.txt` matched a fresh `check.sh` run. Results are in `results/full2` (gitignored), re-graded after the grader fixes below with `run.py --regrade`.

| Case | With skill | Without skill | Checks that split the arms (with 3/3, without 0/3) | With: time, cost per run | Without: time, cost per run |
|---|---|---|---|---|---|
| `fanout-six` | 1.00 | 0.48 | 7 of 11 | 104 s, $1.22 | 54 s, $1.01 |
| `judgment-piece` | 1.00 | 0.50 | 7 of 12 | 83 s, $0.90 | 47 s, $0.68 |
| `two-piece` | 1.00 | 0.52 | 7 of 13 | 61 s, $0.60 | 44 s, $0.48 |
| `no-swarm` | 1.00 | 1.00 | 0 of 3 (expected: should-not-fire) | 8 s, $0.11 | 9 s, $0.11 |

The seven checks that split the arms in every swarm case are the brief contents, the verifiers, the per-agent model, the ledger, the `merge-base` check, plus the case's own model or count check. Without the skill, the baseline still gets the code right: `tests-pass`, `contract-intact` and `cleaned-up` pass 3/3 in both arms. So on tasks this small, the skill changes how the work is done and what it costs, not whether it's correct.

**Grader calibration before this run** (on the first run's traces, via `--regrade`):

- `ledger-kept` matched the `ledger/` package name in `judgment-piece`'s baseline. It now needs a ledger *file* (`ledger.md`, `.txt`, `.tsv`, `.json`).
- The ownership clause in `builder-briefs-complete` missed "Only edit X", "create ONLY", "Touch NO other file" and "Never edit". All are now accepted.

**Grader fix after this run:** in two `two-piece` runs, the client builder and its verifier used a `python3 -c "..."` done-check with the exact expected output instead of `unittest`. That is a valid done-check, so both brief checks now accept `unittest`, `pytest` or `python3 -c`. Before the fix, `two-piece` scored 0.90 with the skill.

**Skill reds:** none in this run. On the first run's traces, the stricter graders found two:

- the batched verifier from before the one-branch rule;
- all three `judgment-piece` integrators skipped `git merge-base` and ported files with `git checkout <branch> -- <paths>`.

Both passed 3/3 in this run.


### 2026-10-08: first full run (original graders)

Linux cloud container, `claude` 2.1.294, Opus integrator, sonnet judge, 3 runs per case and arm, `-j 3`. Agent cost $14.92 for the 24 runs, plus $3.62 for the recheck. Every `check-output.txt` was confirmed by rerunning `check.sh` in the run's repo.

| Case | With skill | Without skill | With: time, cost per run | Without: time, cost per run |
|---|---|---|---|---|
| `fanout-six` | 0.96 (recheck 1.00) | 0.56 | 98 s, $1.10 (recheck ~105 s, $1.20) | 50 s, $1.01 |
| `judgment-piece` | 1.00 | 0.60 | 77 s, $0.87 | 51 s, $0.70 |
| `two-piece` | 1.00 | 0.62 | 62 s, $0.62 | 38 s, $0.46 |
| `no-swarm` | 1.00 | 1.00 | 8 s, $0.11 | 8 s, $0.10 |

**What the skill changes.** Without it, the integrator still splits the work into worktree agents and gets the code right: tests, contract and cleanup pass 3/3 in both arms. But every one of those agents runs with no `model`, so it inherits Opus, and nothing verifies a branch. With the skill:

- builders run on Haiku (6 per `fanout-six` run, 3-4 per `judgment-piece` run, 2 per `two-piece` run);
- each branch gets an Opus verifier at low effort;
- every builder brief carries the git hygiene rules;
- the `two-piece` swarm reaches the 3-agent floor without inventing a third piece.

The price is time and a little money. Verification adds a second round, so runs take 1.5-2x as long and cost 15-35% more. These pieces are small. The cost gap should narrow on larger pieces, where Haiku's lower per-token price outweighs the fixed verifier cost, but this suite doesn't measure that.

**Reds and what they were:**

- **Skill, fixed.** The first pilot ran no verifiers at all. The skill allowed skipping them for small pieces, so `SKILL.md` now requires one per builder. Then `fanout-six` with-1 batched six branches into three verifiers. `SKILL.md` now says one branch per verifier, and the recheck passed `verifiers-opus-low` 3/3.
- **Grader, fixed.** `debugging-on-bigger-model` failed all three with-skill `judgment-piece` runs. In each, the integrator read `totals.py`, found the `int(float * 100)` truncation itself, and gave Haiku a brief with the exact fix. That is the skill's own rule for Haiku: the brief states the files, the contract and the check. The grader is now `debugging-brief-fits-model`: sonnet or opus, or haiku with a brief that names the truncation.
- **Harness.** `claude plugin eval` refuses worktree isolation, hence `run.py` (see above).

## Known gaps

- `judgment-piece` no longer forces a bigger model. The bug is findable from one file, so the integrator diagnoses it first. A case whose root cause needs a multi-file investigation would test the "raise to sonnet" rule.
- No case reaches the 12-builder ceiling, uses waves with a dependency between them, or needs scouts. `fanout-six` tests 6 builders in one wave.
- No case exercises *escalate, don't retry in place*: every Haiku builder passed verification on the first try.
- Rate-limit behavior at 8+ concurrent builders is untested.
- `reports-models` and `relays-root-cause` are LLM checks on the reply. Both were unanimous in every run, but they haven't been calibrated against hand-written wrong replies.
