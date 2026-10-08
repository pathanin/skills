# worktree-swarm evals

How to run the `worktree-swarm` eval suite, what each check measures, and the recorded results.

## What the suite tests

Four cases. Each scaffolds a small stdlib-Python git repo with a `check.sh` acceptance script; the prompt tells the agent to finish with `./check.sh > check-output.txt`. Every case pins the integrator to Opus (`model: opus` in its `prompt.md`), so the builder, scout and verifier models are the skill's choice, not the session's. Don't pass `--model`, because it overrides that pin.

| Case | Setup | Right outcome |
|---|---|---|
| `fanout-six` | `unitconv` needs six unit modules behind a pinned `registry.py` contract. Tests and spec exist. | 5-9 worktree builders on haiku, Opus verifiers at low effort, all 20 tests pass, `registry.py` and tests untouched, no worktree or agent branch left. Old skill capped at 4 pieces, so this is the ceiling check. |
| `two-piece` | Username validation on the server plus its client message. The prompt leaves the error code's name open. | 2-3 worktree builders on haiku, the code pinned in both briefs, at least 3 agents in total (verifiers make up the floor; no padded third piece), all tests pass. |
| `judgment-piece` | Three mechanical modules from `SPEC.md`, plus "totals are sometimes a cent low, nobody knows why". | Mechanical pieces on haiku, the debugging piece on sonnet or opus, Opus low-effort verifiers, all 8 tests pass, and the reply names the real cause (`int()` truncating `float * 100`). |
| `no-swarm` | A one-line off-by-one in `paginate`. The prompt doesn't mention swarming. | Fixed directly, with no worktree agents. Should-not-fire case. |

### How the checks measure

- **Outcome checks** read `check-output.txt`, which `check.sh` writes by running the suite and git itself. An agent could hand-write that file, so when a pass looks surprising, rerun `./check.sh` in the run's `repo`:
  - `tests-pass`: `CHECK RESULT: PASS (N tests)` with N at least the fixture's test count, so deleting tests fails it.
  - `contract-intact`: `sha256sum -c` over the files the task must not change (the registry contract, the tests, the spec).
  - `cleaned-up`: `git worktree list` and `git branch --list 'worktree-*' '*agent*' 'swarm/*'` both empty.
- **Swarm-shape checks** are `tool_used` graders on the integrator's `Agent` calls. `input_match` is a JS regex (no flags) tested against each call's input as JSON, so lookaheads pick out a field regardless of key order:
  - `builders-haiku`: `isolation: worktree` and `model: haiku`, with a min and max count.
  - `verifiers-opus-low`: no isolation, `model: opus`, `effort: low`, and the prompt mentions `diff`.
  - `no-other-verifier-model`: any non-worktree call whose prompt says `git ... diff` (a verifier) without both `opus` and `low` fails the case.
  - `every-agent-has-model`: no `Agent` call omits `model`.
  - `debugging-on-bigger-model` (judgment-piece): a worktree builder on sonnet or opus whose brief mentions totals.
- **LLM checks** only grade the reply: `reports-models` (fanout-six) and `relays-root-cause` (judgment-piece).

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

See the dated sections below.
