# fresh-start evals

How to run the `fresh-start` eval suite on your own machine, and how to read the result.

## What the suite tests

Two cases, each run 3 times by default.

| Case | Setup | Right outcome |
|---|---|---|
| `tangled` | A messy `shipping_cost` in a git repo. You ask for free shipping over 100. | Rewrite it simply, keep the BT/JE/GY/IM +4.00 surcharge, tell you about the EU express bug, run the tests, leave one implementation. |
| `clean-keep` | A small, clean, tested `slugify`. You ask for a `max_length` option. | Keep the old code, add the option correctly, run the tests, say the old version won. |

The two traps in `tangled`:

- **EU express bug.** EU orders with `express=True` never pay the 8.00 fee in the old code, and no test covers it. The skill should report it, not silently keep or silently fix it.
- **Surcharge.** The reason for the BT/JE/GY/IM surcharge is only in a git commit message. The skill should read history before deciding what to keep.

## Before you run

1. **Claude Code is installed and logged in.** Check with `claude --version`.
2. **The sandbox works.** The eval refuses to give the agent a shell it can't sandbox.
   - **macOS:** nothing to install.
   - **Linux:** install bubblewrap and socat:
     ```bash
     sudo apt install bubblewrap socat
     ```
   - **Inside a container** (Docker, a cloud dev box): the nested sandbox usually fails with `write /proc/self/uid_map: Operation not permitted`. Add this to `~/.claude/settings.json`:
     ```json
     { "sandbox": { "enableWeakerNestedSandbox": true } }
     ```
3. **You have the latest main.**
   ```bash
   git checkout main && git pull
   ```

To confirm the sandbox before spending money on a full run:

```bash
claude -p "Run this bash command and print its raw output: echo ok && python3 -c 'print(2+2)'" \
  --allowedTools Bash --settings '{"sandbox":{"enabled":true,"failIfUnavailable":true}}'
```

It should print `ok` and `4`. If it prints a sandbox or `uid_map` error instead, go back to step 2.

## Run it

From the skill directory:

```bash
cd internal-tools/fresh-start
claude plugin eval . --runs 3 --ablation none --scaffold --trust-plugin \
  --allow-tools Write Edit Bash -j 3 --keep-temp
```

What the flags do:

- `--ablation none`: skip the no-plugin baseline. `fresh-start` is manual-only, so a baseline can't reach it anyway.
- `--scaffold`: run each case's `fixture.sh` to build the test repo.
- `--allow-tools Write Edit Bash`: let the agent edit files and run tests.
- `-j 3`: run 3 agents at once. Drop it for a slower, quieter run.
- `--keep-temp`: keep each run's working directory and trace, so you can see what the agent actually ran. Without it, traces are deleted after the run.
- Add `--no-publish` if you don't want the HTML report uploaded to claude.ai.

Expect about 4–10 minutes and roughly $1.50–2.50 for 6 runs.

To run one case only, add `--case tangled` or `--case clean-keep`.

## Read the result

The command prints a report path like `evals/results/<timestamp>/report.html`. Open it. The `results/` directory is gitignored.

**First, rule out an environment failure.** If most checks fail, open one run's final message in the report. If it says Bash was unavailable or the sandbox failed, the run is invalid. Fix the sandbox (see "Before you run") and run again.

**Then look at these checks:**

| Check | What it tells you |
|---|---|
| `max-length` (clean-keep) | Whether the skill tests the new behavior itself. The step-4 "cases for the requested change" line was added for this. |
| `ran-tests` (both) | Whether the agent actually ran the test suite. |
| `read-history` (tangled) | Whether the agent read `git log`/`blame` before deciding what to keep. |
| `surfaces-eu-express` (tangled) | Whether the agent reports pre-existing bugs it finds. |
| `says-old-won` (clean-keep) | Whether the skill avoids rewriting code that is already fine. |

**When a check fails**, read the judge's evidence in the report before changing the skill. Decide which of these it is:

- **The skill is wrong:** the agent really did the wrong thing. Fix `SKILL.md`.
- **The grader is wrong:** the agent's code or reply was correct but the check rejected it. Fix the file in `graders/`.

## Previous run (for comparison)

This run was on 2026-09-23 in a cloud container where **Bash was broken inside the sandbox**. Agents could read and edit files but couldn't run tests or `git log`. The step-4 line and the grader fixes came after it.

| Check | Pass | Note |
|---|---|---|
| tangled: `keeps-surcharge` | 3/3 | |
| tangled: `surfaces-eu-express` | 3/3 | |
| tangled: `no-leftover` | 3/3 | |
| tangled: `report-shape` | 2/3 | |
| tangled: `free-shipping` | 1/3 | Both failed code looked correct on reading. The grader didn't allow either EU express choice, and has since been fixed. |
| tangled: `simpler` | 2/3 | The failure rejected a plain `is_eu = ...` line. Grader since fixed. |
| clean-keep: `kept-pipeline` | 3/3 | |
| clean-keep: `says-old-won` | 2/3 | |
| clean-keep: `max-length` | 1/3 | A real bug: the cut dropped a whole word at an exact boundary. |
| `ran-tests`, `read-history` | — | Not meaningful: Bash didn't work. |

## Known gaps

- The surcharge trap is weaker than intended: the surcharge is visible in the current code, so a rewrite keeps it even without reading history. `read-history` is the only check that the agent looked.
- There is no case where the right answer is **hybrid**, and none where the skill should **stop and ask** (no tests, or external callers depend on the behavior).
