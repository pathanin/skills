# fresh-start evals

How to run the `fresh-start` eval suite on your own machine, and how to read the result.

## What the suite tests

Three cases, each run 3 times by default.

| Case | Setup | Right outcome |
|---|---|---|
| `tangled` | A messy `shipping_cost` in a git repo. You ask for free shipping over 100 ("shipping is free, except express"). | Rewrite it simply, keep the BT/JE/GY/IM +4.00 surcharge on free orders and say why, keep the `shipping_zone` write, tell you about the EU express bug, run the tests, leave one implementation. |
| `clean-keep` | A small, clean, tested `slugify`. You call it clunky, invite a rewrite, and ask for a `max_length` option. | Keep the old code anyway, add the option correctly, run the tests, say the old version won. |
| `stored-format` | A messy, untested `record_path` whose daily filenames are year-day-month, with existing files in `data/` under those names. You ask for a cleanup and weekly files. | Keep the daily names exactly as they are and report the day/month order, or stop and ask. Never rename the data. If weekly is added, it uses the ISO year. |

The traps in `tangled`:

- **Surcharge on free orders.** The surcharge is folded into the base rate, so zeroing the base for free shipping also drops it. Only the surcharge's commit message says it is a carrier pass-through that must be charged on free orders too. The skill should read history, keep it, and tell you why.
- **Zone side effect.** `shipping_cost` writes `order["shipping_zone"]`, and `invoice.py` reads it afterwards. No test covers it. A "pure function" rewrite that drops the write breaks invoices.
- **EU express bug.** EU orders with `express=True` never pay the 8.00 fee in the old code, and no test covers it. The skill should report it, not silently keep or silently fix it.

The trap in `stored-format`: rewriting the date as `strftime("%Y%m%d")` looks like a fix, but it orphans every stored file. The skill's step 5 says to stop and ask when the fresh version changes behavior that stored data depends on. Asking without editing anything passes.

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
  --allow-tools Write Edit Bash --judge-model sonnet -j 3 --keep-temp
```

What the flags do:

- `--ablation none`: skip the no-plugin baseline. `fresh-start` is manual-only, so a baseline can't reach it anyway.
- `--scaffold`: run each case's `fixture.sh` to build the test repo.
- `--allow-tools Write Edit Bash`: let the agent edit files and run tests.
- `--judge-model sonnet`: the LLM checks judge code by reading it, and the default haiku judge misses too much.
- `-j 3`: run 3 agents at once. Drop it for a slower, quieter run.
- `--keep-temp`: keep each run's working directory and trace, so you can see what the agent actually ran. Without it, traces are deleted after the run.
- Add `--no-publish` if you don't want the HTML report uploaded to claude.ai.

Expect about 4 minutes and roughly $3 for 9 runs with `-j 3`.

To run one case only, add `--case <name>`, e.g. `--case stored-format`.

## Read the result

The command prints a report path like `evals/results/<timestamp>/report.html`. Open it. The `results/` directory is gitignored.

**First, rule out an environment failure.** If most checks fail, open one run's final message in the report. If it says Bash was unavailable or the sandbox failed, the run is invalid. Fix the sandbox (see "Before you run") and run again.

**On macOS, `git` fails inside the eval sandbox.** The eval's shell finds `/usr/bin/git`, the Xcode shim, which fails with `couldn't create cache file '.../xcrun_db-...' (errno=Operation not permitted)`. The smoke check above doesn't catch this, because a plain `claude -p` finds your usual `git`. Agents work around it by using `/opt/homebrew/bin/git` or by reading `.git/objects` with Python. So `read-history` passes on a `git log` call even if that call errored. `explains-surcharge` is the check that the agent actually got the history. If a trace shows the xcrun error and no fallback, a surcharge failure in that run comes from the environment, not a clean signal about the skill.

**Then look at these checks:**

| Check | What it tells you |
|---|---|
| `max-length` (clean-keep) | Whether the skill tests the new behavior itself. The step-4 "cases for the requested change" line was added for this. |
| `ran-tests` (both) | Whether the agent actually ran the test suite. |
| `read-history` (tangled) | Whether the agent read `git log`/`blame` before deciding what to keep. |
| `keeps-surcharge`, `explains-surcharge` (tangled) | Whether the agent acted on a rule that exists only in a commit message. |
| `keeps-zone` (tangled) | Whether the agent read callers and kept a side effect that no test covers. |
| `daily-unchanged`, `flags-day-month`, `data-untouched` (stored-format) | Whether the agent protects stored data instead of "fixing" what looks like a bug. |
| `surfaces-eu-express` (tangled) | Whether the agent reports pre-existing bugs it finds. |
| `says-old-won` (clean-keep) | Whether the skill avoids rewriting code that is already fine. |

**When a check fails**, read the judge's evidence in the report before changing the skill. Decide which of these it is:

- **The skill is wrong:** the agent really did the wrong thing. Fix `SKILL.md`.
- **The grader is wrong:** the agent's code or reply was correct but the check rejected it. Fix the file in `graders/`.

## Previous runs (for comparison)

Three runs on 2026-09-25, macOS, Opus 5.5, sonnet judge, `-j 3`. About $7 in total.

1. **Run 1:** all 3 cases.
2. **Run 2:** all 3 cases, after the `weekly` and `free-shipping` rubric fixes.
3. **Run 3:** `tangled` only.

Every red below was checked by running the agent's code, rebuilt from `out/trace.jsonl`. Each red is marked as one of:

- **real:** the agent really got it wrong.
- **ask:** the run stopped to ask. A fail is correct for unfinished work.
- **judge:** the code ran correctly, but the judge failed it.

| Check | Run 1 | Run 2 | Run 3 | Reds |
|---|---|---|---|---|
| clean-keep: all 5 checks | 3/3 | 3/3 | — | |
| stored-format: `daily-unchanged`, `data-untouched`, `flags-day-month`, `no-leftover` | 3/3 | 3/3 | — | |
| stored-format: `weekly` | 1/3 | 3/3 | — | Run 1: 2 judge. All three agents used `isocalendar()` correctly; the old rubric made the judge compute ISO weeks. Rewritten after run 1. |
| tangled: `keeps-zone`, `no-leftover`, `read-history`, `surfaces-eu-express` | 3/3 | 3/3 | 3/3 | |
| tangled: `keeps-surcharge`, `explains-surcharge` | 3/3 | 2/3 | 3/3 | Run 2: 1 real. The agent waived the surcharge on free orders. Its `git log` hit the xcrun error and it never fell back, so it never saw the commit. |
| tangled: `free-shipping` | 1/3 | 2/3 | 1/3 | Run 1: 2 judge. Run 2: 1 judge. Run 3: 1 judge, 1 ask. The `<=` clarification added after run 1 did not remove the noise. |
| tangled: `simpler` | 2/3 | 0/3 | 1/3 | Run 1: 1 judge. Run 2: 3 judge. Run 3: 1 judge, 1 ask. The judged-out code had no flags, no dead branches, and each rule once. |
| tangled: `ran-tests`, `report-shape` | 3/3 | 3/3 | 2/3 | Run 3: 1 ask. |

The one ask-path run stopped over the EU express fee: "Unexplained, ask" and "Old bug, report" both fit, and the skill leaves the choice open. `keeps-surcharge` and `explains-surcharge` passed it as designed.

**`free-shipping` and `simpler` are unreliable.** Run the agent's code before trusting a red on either. A standalone `claude -p --model sonnet` with the same rubric and code passes code that the eval judge fails unanimously, so a standalone check can't tell you what the eval judge will say.

## Known gaps

- **The suite barely catches the skill failing.** In 21 runs the only real trap miss was the surcharge in one run where `git` was broken. Each trap is a fact the agent can find in a repo of three files or fewer, usually with one `cat` + `git log -p` + `grep`. To make it harder without depending on git, use more files, so the contract doesn't all show up in the agent's first read.
- **`free-shipping` asks whether orders "price exactly as the old code did", but its judge only sees the new `pricing.py`.** This is the leading guess for its noise. Fix: put the old rates in the rubric (GB 6.00, EU 5.00, rest 15.00; +1.50/kg, or +3.00/kg for the rest of the world, over 2 kg; express +8.00 except EU). This fix is untested.
- The ask-path clauses in `weekly` and `flags-day-month` have never been exercised. No `stored-format` run has stopped to ask.
- `tangled` expects the agent to finish. An agent that stops to ask about the surcharge passes `explains-surcharge` but fails the checks that need code.
- No case covers step 5's third stop condition: the user asks for a minimal change and the rewrite touches far more lines.
- There is no case where the right answer is **hybrid**.
- `max-length` and `daily-unchanged` also ask the judge to work out outputs by reading the code. They have been 6/6 so far, but they are the same kind of check that made `weekly` fail. If one fails, run the agent's code before trusting the verdict. `--keep-temp` seals the working directory, but `out/trace.jsonl` has every Write, Edit and Bash call. Agents often write code through a Bash heredoc into `$TMPDIR` and then `cp` it.
