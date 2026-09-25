# fresh-start evals

How to run the `fresh-start` eval suite on your own machine, and how to read the result.

## What the suite tests

Four cases, each run 3 times by default. Every case pins the agent to Sonnet (`model: sonnet` in its `prompt.md`). Don't pass `--model`, because it overrides that.

| Case | Setup | Right outcome |
|---|---|---|
| `tangled` | A messy `shipping_cost` in a git repo. You ask for free shipping over 100 ("shipping is free, except express") and say to fix any bugs found along the way. | Rewrite it simply, keep the BT/JE/GY/IM +4.00 surcharge on free orders and say why, keep the `shipping_zone` write, tell you about the EU express bug, run the tests, leave one implementation. |
| `clean-keep` | A small, clean, tested `slugify`. You call it clunky, invite a rewrite, and ask for a `max_length` option. | Keep the old code with its lines untouched, add the option correctly, run the tests, say the old version won. |
| `finance-export` | A 22-file repo. You ask for a cleanup of the nightly export, for test orders (`@example.com`) to be skipped, and for each order's country to be added. | Add the country as finance's importer specifies, which is written down only in finance's files. Keep every other byte of the output, keep the write-then-rename, handle `None` fields, run and update the tests, and tie the format to finance's importer. Expects the agent to finish, not ask. |
| `stored-format` | A messy, untested `record_path` whose daily filenames are year-day-month, with existing files in `data/` under those names. You ask for a cleanup and weekly files. | Keep the daily names exactly as they are and report the day/month order, or stop and ask. Never rename the data. If weekly is added, it uses the ISO year. |

The traps in `tangled`:

- **Surcharge on free orders.** The surcharge is folded into the base rate, so zeroing the base for free shipping also drops it. Only the surcharge's commit message says it is a carrier pass-through that must be charged on free orders too. The skill should read history, keep it, and tell you why.
- **Zone side effect.** `shipping_cost` writes `order["shipping_zone"]`, and `invoice.py` reads it afterwards. No test covers it. A "pure function" rewrite that drops the write breaks invoices.
- **EU express bug.** EU orders with `express=True` never pay the 8.00 fee in the old code, and no test covers it. The prompt authorizes bug fixes, so fixing it is fine, but the reply must say so.

The traps in `finance-export` are spread out so that a first look (list the top level, `cat` the target, `grep` for callers) misses them. There's one commit, so git history doesn't help:

- **Country column.** The requested column must be named `country_code`, placed last, written in capitals, and set to `ZZ` when unknown. That spec exists only in `docs/finance-export.md` and `vendor/finance/importer.py`, and the prompt doesn't name either file. Copying the old code can't produce it. This is the trap that needs the agent to find the consumer.
- **Output format.** Finance's parser splits on `\n` and `,` and rejects `\r` and `"`. The idiomatic cleanup, `csv.writer`, defaults to CRLF and quotes names containing commas. The existing tests read the file in text mode, so they can't see either.
- **Write-then-rename.** The `.tmp` + `os.replace` is explained only in an incident note in `docs/runbook.md`.
- **`None` fields.** `shopkit/orders.py` (the loader the nightly job uses) produces `customer`, `email`, `currency` and `country` set to `None`. `.get(key, default)` doesn't replace those, and no test passes `None`.

The existing header and row tests fail under any correct version, because the header gains a column. The agent is expected to update them.

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

Expect about 9 minutes and roughly $4.50 for 12 Sonnet runs with `-j 3`.

To run one case only, add `--case <name>`, e.g. `--case stored-format`.

## Next run: calibrate first, then measure the skill fix

Several graders changed after the last run and haven't been checked in the harness yet (see "Uncalibrated graders" below). Before a full run:

1. **Calibrate the changed LLM graders.** Make a throwaway eval dir, e.g. `evals-calib/`, with one case per known version of the target file. Its `fixture.sh` writes that version, and its prompt asks for a fixed reply. Run it with `--eval-dir evals-calib --runs 2`. Each grader should pass the good versions and fail the bad ones unanimously. Delete the directory afterwards.
   - Use as known versions code whose behavior you've confirmed by running it: a hand-written reference, plus real agent outputs rebuilt from `out/trace.jsonl`.
   - `--keep-temp` seals the working directory, but `out/trace.jsonl` has every Write, Edit and Bash call. Agents often write code through a Bash heredoc into `$TMPDIR` and then `cp` it.
   - Sonnet refuses to recite an unverified claim, even when told it's a calibration. A reply check therefore needs a few runs before you get one reply that actually says it.
2. **Measure the `SKILL.md` fix.** `SKILL.md` changed in `a42fe06`, separately from the graders. Run the current suite twice, once with the skill as it was before that commit and once at HEAD. Both runs use the same graders, so the difference is the skill's effect:
   ```bash
   git show a42fe06~1:internal-tools/fresh-start/SKILL.md > SKILL.md   # before
   claude plugin eval . ...   # same command as above
   git checkout SKILL.md                                               # back to HEAD
   claude plugin eval . ...
   ```

## Read the result

The command prints a report path like `evals/results/<timestamp>/report.html`. Open it. The `results/` directory is gitignored. For each LLM check, the report shows "Evidence (what the judge was shown)", but not the judge's reasoning.

**First, rule out an environment failure.** If most checks fail, open one run's final message in the report. If it says Bash was unavailable or the sandbox failed, the run is invalid. Fix the sandbox (see "Before you run") and run again.

**On macOS, `git` fails inside the eval sandbox.** The eval's shell finds `/usr/bin/git`, the Xcode shim, which fails with `couldn't create cache file '.../xcrun_db-...' (errno=Operation not permitted)`. The smoke check above doesn't catch this, because a plain `claude -p` finds your usual `git`. Most agents work around it by using `/opt/homebrew/bin/git`, `env HOME=$TMPDIR git`, or reading `.git/objects` with Python. Some give up. `read-history` passes only if the surcharge commit's text shows up in the trace, so a failed `git` call no longer counts. If a run gave up on `git`, its surcharge failures come from the environment, not a clean signal about the skill. Since `a42fe06`, the skill tells the agent to say so in its reply.

**Then look at these checks:**

| Check | What it tells you |
|---|---|
| `max-length` (clean-keep) | Whether the agent worked out expected outputs for the new behavior from the request, including the exact-limit case. |
| `old-lines-kept`, `says-old-won` (clean-keep) | Whether the agent left already-fine code alone on a tie: the old lines untouched, and the reply says the old version won. |
| `ran-tests` (clean-keep, tangled, finance-export) | Whether the agent actually ran the test suite. |
| `read-history` (tangled) | Whether the surcharge commit's text actually reached the agent. |
| `keeps-surcharge`, `explains-surcharge` (tangled) | Whether the agent acted on a rule that exists only in a commit message. |
| `keeps-zone` (tangled) | Whether the agent read callers and kept a side effect that no test covers. |
| `no-flags`, `simpler` (tangled) | Whether the rewrite drops the `done`/`cost = None` flags and computes the weight charge and express fee in one place each. |
| `country-column` (finance-export) | Whether the agent found the consumer's spec for the new column. Copying the old code can't pass this one. |
| `plain-format`, `atomic-write`, `none-fields` (finance-export) | Whether the agent kept facts that live outside the target file and its direct callers. |
| `explains-format` (finance-export) | Whether the agent can say *why* the format is what it is. |
| `daily-unchanged`, `flags-day-month`, `data-untouched` (stored-format) | Whether the agent protects stored data instead of "fixing" what looks like a bug. |
| `surfaces-eu-express` (tangled) | Whether the agent reports pre-existing bugs it finds. |

**When a check fails**, read the judge's evidence in the report before changing the skill. Decide which of these it is:

- **The skill is wrong:** the agent really did the wrong thing. Fix `SKILL.md`.
- **The grader is wrong:** the agent's code or reply was correct but the check rejected it. Fix the file in `graders/`.

For an LLM check on code, run the agent's code before trusting a red. Past judges have failed code that ran correctly.

## Uncalibrated graders

Changed after the last run and not yet checked in the harness:

- **LLM, need calibration:**
  - `tangled`: `free-shipping` (now lists every rate and condition instead of saying "same as the old code"), `simpler` (now counts places instead of judging the whole file).
  - `clean-keep`: `says-old-won` (now fails any reported rework of the old lines).
  - `finance-export`: `country-column` (new), `explains-format` (rewritten for the country column).
- **Regex, checked locally against saved outputs:**
  - `no-flags` fails only the old `pricing.py`.
  - `old-lines-kept` passes the original and a correct keep-plus-feature version, and fails all three Sonnet edits.
  - `read-history`, run over each run's `trace.jsonl`, passes exactly the runs that saw the commit.
  - One thing is unverified: whether the harness's `target: trace` includes tool output the way `trace.jsonl` does. On the next run, compare `read-history` against `grep -c 'carrier pass-through, not part of our rate' <run>/out/trace.jsonl`.

## Sonnet baseline (2026-09-25)

One run, macOS, `claude-sonnet-5` agent (checked in each trace's `init` line; no subagents), sonnet judge, 3 runs per case, `-j 3`: 9 minutes, $4.47. Reds use the same labels as the Opus table below, plus **grader** for a check that is too literal.

**Not comparable with the current suite.** After this run, `SKILL.md` changed (`a42fe06`). So did these parts of the suite:

- the `tangled` and `finance-export` prompts
- `free-shipping`, `simpler`, `read-history`, `says-old-won` and `explains-format`
- new checks: `no-flags` and `country-column`
- `kept-pipeline`, replaced by `old-lines-kept`

| Check | Pass | Reds |
|---|---|---|
| clean-keep: `max-length` | 0/3 | 3 real. All three drop a whole word when the cut lands exactly at a word's end: `slugify("hello world foo", max_length=11)` gives `"hello"`, not `"hello-world"`. One run says it tested "exact word boundary", with an expected value that matched its own bug. |
| clean-keep: `says-old-won`, `kept-pipeline` | 1/3, 2/3 | Every run edited the old lines, even though the fresh version only tied. OI6srW called it a "fresh rewrite" and reordered the pipeline. The other two made nearly the same rename-only edit, and the old graders split them in opposite directions based on reply wording. Both graders were replaced. |
| clean-keep: `ran-tests`, `no-leftover` | 3/3 | |
| finance-export: `plain-format`, `atomic-write`, `none-fields`, `skips-test-orders` | 3/3 | All three runs' code passed finance's importer and every behavior check when run. |
| finance-export: `explains-format` | 0/3 | 3 real. No tool output in any run contains text from `docs/finance-export.md` or `vendor/finance/importer.py`, not even the path. The agents kept the format by copying behavior line by line. One read `docs/runbook.md`. |
| finance-export: `ran-tests`, `no-leftover` | 3/3 | |
| stored-format: all 5 checks | 3/3 | Code rebuilt from the traces and run: the daily paths are unchanged and the ISO weeks are right in all three. |
| tangled: `keeps-surcharge`, `explains-surcharge` | 2/3 | 1 real, caused by the environment. `git` hit the xcrun error, the agent gave up, and it waived the surcharge on free orders. |
| tangled: `free-shipping` | 1/3 | 2 judge. The code ran correctly, apart from the surcharge that the rubric says to ignore. |
| tangled: other 8 checks | 3/3 | |

What this run changed:

- **`SKILL.md`:**
  - Step 2 now tells the agent to search for readers of the unit's output, not just callers.
  - Step 4 now has the agent work out expected outputs from the request before running any version.
  - Step 5 now says that on a tie the old lines stay untouched, even when the user invites a rewrite.
  - The skill now asks the agent to say when history couldn't be read.
- **`finance-export`:** gained the country column. The code traps in this run only bite an agent that reaches for `csv.writer` or `.get(key, default)`, and copying the old code line by line dodged all of them.

## Opus 5.5 runs (2026-09-25, before the Sonnet pin)

Three runs, macOS, Opus 5.5 agent, sonnet judge, `-j 3`. About $7 in total. `finance-export` did not exist yet. Not comparable with the current suite, for the same reasons as the Sonnet baseline.

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
| stored-format: `weekly` | 1/3 | 3/3 | — | Run 1: 2 judge. The old rubric made the judge compute ISO weeks. Rewritten after run 1. |
| tangled: `keeps-zone`, `no-leftover`, `read-history`, `surfaces-eu-express` | 3/3 | 3/3 | 3/3 | |
| tangled: `keeps-surcharge`, `explains-surcharge` | 3/3 | 2/3 | 3/3 | Run 2: 1 real. `git` hit the xcrun error and the agent never fell back. |
| tangled: `free-shipping` | 1/3 | 2/3 | 1/3 | Run 1: 2 judge. Run 2: 1 judge. Run 3: 1 judge, 1 ask. |
| tangled: `simpler` | 2/3 | 0/3 | 1/3 | Run 1: 1 judge. Run 2: 3 judge. Run 3: 1 judge, 1 ask. |
| tangled: `ran-tests`, `report-shape` | 3/3 | 3/3 | 2/3 | Run 3: 1 ask. |

The one ask-path run stopped over the EU express fee, which raises prices. Step 5's "stop and ask" fits that, so the `tangled` prompt now authorizes bug fixes.

## Known gaps

- The ask-path clauses in `weekly` and `flags-day-month` have never been exercised. No `stored-format` run has stopped to ask.
- `tangled` and `finance-export` expect the agent to finish. An agent that stops to ask passes the reply checks but fails the ones that need code.
- No case covers step 5's third stop condition: the user asks for a minimal change and the rewrite touches far more lines.
- There is no case where the right answer is **hybrid**.
- `max-length`, `daily-unchanged` and `weekly` ask the judge to work out outputs by reading the code. They were right every time they were checked, but they are the same kind of check that once made `weekly` fail.
- **Narrowed coverage:**
  - `simpler` no longer checks for dead branches; `no-flags` covers the old code's dead express branch, because that branch tests `done`.
  - `old-lines-kept` fails any rename of the old lines, which matches the new step-5 rule.
