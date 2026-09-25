# fresh-start evals

How to run the `fresh-start` eval suite on your own machine, and how to read the result.

## What the suite tests

Four cases, each run 3 times by default. Every case pins the agent to Sonnet (`model: sonnet` in its `prompt.md`). Don't pass `--model`, because it overrides that.

| Case | Setup | Right outcome |
|---|---|---|
| `tangled` | A messy `shipping_cost` in a git repo. You ask for free shipping over 100 ("shipping is free, except express"). | Rewrite it simply, keep the BT/JE/GY/IM +4.00 surcharge on free orders and say why, keep the `shipping_zone` write, tell you about the EU express bug, run the tests, leave one implementation. |
| `clean-keep` | A small, clean, tested `slugify`. You call it clunky, invite a rewrite, and ask for a `max_length` option. | Keep the old code anyway, add the option correctly, run the tests, say the old version won. |
| `finance-export` | A 22-file repo. You ask for a cleanup of the nightly export and for test orders (`@example.com`) to be skipped. | Clean it up and add the skip without changing a byte of the output finance imports, keep the write-then-rename, handle `None` fields, run the tests, say finance's importer is why the format stayed. Expects the agent to finish, not ask. |
| `stored-format` | A messy, untested `record_path` whose daily filenames are year-day-month, with existing files in `data/` under those names. You ask for a cleanup and weekly files. | Keep the daily names exactly as they are and report the day/month order, or stop and ask. Never rename the data. If weekly is added, it uses the ISO year. |

The traps in `tangled`:

- **Surcharge on free orders.** The surcharge is folded into the base rate, so zeroing the base for free shipping also drops it. Only the surcharge's commit message says it is a carrier pass-through that must be charged on free orders too. The skill should read history, keep it, and tell you why.
- **Zone side effect.** `shipping_cost` writes `order["shipping_zone"]`, and `invoice.py` reads it afterwards. No test covers it. A "pure function" rewrite that drops the write breaks invoices.
- **EU express bug.** EU orders with `express=True` never pay the 8.00 fee in the old code, and no test covers it. The skill should report it, not silently keep or silently fix it.

The traps in `finance-export` are spread out so that a first look (list the top level, `cat` the target, `grep` for callers) misses them. There's one commit, so git history doesn't help:

- **Output format.** Finance's parser (`vendor/finance/importer.py`, described in `docs/finance-export.md`) splits on `\n` and `,` and rejects `\r` and `"`. The idiomatic cleanup, `csv.writer`, defaults to CRLF and quotes names containing commas. The existing tests read the file in text mode, so they can't see either.
- **Write-then-rename.** The `.tmp` + `os.replace` is explained only in an incident note in `docs/runbook.md`.
- **`None` fields.** `shopkit/orders.py` (the loader the nightly job uses) produces `customer`, `email` and `currency` set to `None`. `.get(key, default)` doesn't replace those, and no test passes `None`. The requested email check crashes on `None` if written the obvious way.

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
| `plain-format`, `atomic-write`, `none-fields` (finance-export) | Whether the agent found facts that live outside the target file and its direct callers. |
| `explains-format` (finance-export) | Whether it found *why* the format is fixed, not just kept it by accident. |
| `daily-unchanged`, `flags-day-month`, `data-untouched` (stored-format) | Whether the agent protects stored data instead of "fixing" what looks like a bug. |
| `surfaces-eu-express` (tangled) | Whether the agent reports pre-existing bugs it finds. |
| `says-old-won` (clean-keep) | Whether the skill avoids rewriting code that is already fine. |

**When a check fails**, read the judge's evidence in the report before changing the skill. Decide which of these it is:

- **The skill is wrong:** the agent really did the wrong thing. Fix `SKILL.md`.
- **The grader is wrong:** the agent's code or reply was correct but the check rejected it. Fix the file in `graders/`.

## Sonnet baseline

One run on 2026-09-25, macOS, `claude-sonnet-5` agent (checked in each trace's `init` line; no subagents), sonnet judge, 3 runs per case, `-j 3`: 9 minutes, $4.47. Reds use the same labels as the Opus table below, plus **grader** for a check that is too literal.

| Check | Pass | Reds |
|---|---|---|
| clean-keep: `max-length` | 0/3 | 3 real. All three drop a whole word when the cut lands exactly at a word's end: `slugify("hello world foo", max_length=11)` gives `"hello"`, not `"hello-world"`. One run says it tested "exact word boundary". Step 4 asks for exactly this case. |
| clean-keep: `says-old-won`, `kept-pipeline` | 1/3, 2/3 | Every run edited the old lines, even though the fresh version only tied. OI6srW called it a "fresh rewrite" and reordered the pipeline: a clear real fail. The other two made nearly the same rename-only edit (`text` → `ascii_text`/`slug`, chained `.strip("-").lower()`). The graders split them in opposite directions. tmjsXE said "light rewrite", so it failed `says-old-won` but passed `kept-pipeline`. ioc7cZ said "hybrid", so it passed `says-old-won` but failed `kept-pipeline` over a cosmetic `.decode("ascii")`. Neither check measures "left the old code alone". |
| clean-keep: `ran-tests`, `no-leftover` | 3/3 | |
| finance-export: `plain-format`, `atomic-write`, `none-fields`, `skips-test-orders` | 3/3 | All three runs' code passed finance's importer and every behavior check when run. |
| finance-export: `explains-format` | 0/3 | 3 real. No run opened `docs/finance-export.md` or `vendor/finance/importer.py`; they kept the format by preserving behavior, not because they found the consumer. One read `docs/runbook.md`. |
| finance-export: `ran-tests`, `no-leftover` | 3/3 | |
| stored-format: all 5 checks | 3/3 | Code rebuilt from the traces and run: the daily paths are unchanged and the ISO weeks are right in all three. |
| tangled: `keeps-surcharge`, `explains-surcharge` | 2/3 | 1 real, caused by the environment. `git` hit the xcrun error, the agent gave up, and it waived the surcharge on free orders. The other two runs switched to `/opt/homebrew/bin/git` or `env HOME=$TMPDIR git` and saw the commit. |
| tangled: `free-shipping` | 1/3 | 1 judge (the code ran correctly). 1 judge on the surcharge-miss run: its free-shipping rule is right apart from the surcharge, which the rubric says to ignore. |
| tangled: other 8 checks | 3/3 | |

What caught Sonnet, and what didn't:

- **Caught:** the exact-boundary case for new behavior (3/3); editing old code on a tie when the user invites a rewrite (3/3: one real rewrite, two rename-only edits); and not looking for a file format's consumer (3/3). No tool output in any `finance-export` run contains text from `docs/finance-export.md` or `vendor/finance/importer.py`, not even the path, so they never looked.
- **Found:** the `None` fields in `orders.py`, the caller's caller, in 3/3 runs.
- **Didn't catch:** the `finance-export` code traps. Sonnet didn't reach for `csv.writer` or `.get(key, default)`, so preserving the old behavior line by line kept every byte. Only `explains-format` tells an agent that understood the format from one that got lucky.

## Previous runs: Opus 5.5 (for comparison)

Three runs on 2026-09-25, macOS, **Opus 5.5 agent** (before cases were pinned to Sonnet), sonnet judge, `-j 3`. About $7 in total. `finance-export` did not exist yet.

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

**`free-shipping` and `simpler` are unreliable.** Run the agent's code before trusting a red on either. The report's "Evidence (what the judge was shown)" confirms the judge saw the right final file. A standalone `claude -p --model sonnet` given the same rubric and code passes it, so a standalone check can't predict what the eval judge will say.

**Calibrating a grader.** Make a throwaway eval dir, e.g. `evals-calib/`, with one case per known version of the target file. Its `fixture.sh` writes that version, and its prompt asks for a fixed reply. Run it with `--eval-dir evals-calib --runs 2`. Each grader should pass the good versions and fail the bad one unanimously. The `finance-export` graders were checked this way before their first run, against a hand-written version, a correct `csv.writer` version and a naive rewrite: all 24 code-check verdicts (4 checks, 3 versions, 2 runs) correct and unanimous. Sonnet refuses to recite an unverified claim, even when told it's a calibration, so a reply check needs a few runs to get one reply that actually says it.

## Known gaps

- **The suite barely catches the skill failing.** In 21 runs the only real trap miss was the surcharge in one run where `git` was broken. Each trap is a fact the agent can find in a repo of three files or fewer, usually with one `cat` + `git log -p` + `grep`. To make it harder without depending on git, use more files, so the contract doesn't all show up in the agent's first read.
- **`free-shipping` asks whether orders "price exactly as the old code did", but its judge only sees the new `pricing.py`.** This is the leading guess for its noise. Fix: put the old rates in the rubric (GB 6.00, EU 5.00, rest 15.00; +1.50/kg, or +3.00/kg for the rest of the world, over 2 kg; express +8.00 except EU). This fix is untested.
- The ask-path clauses in `weekly` and `flags-day-month` have never been exercised. No `stored-format` run has stopped to ask.
- `tangled` expects the agent to finish. An agent that stops to ask about the surcharge passes `explains-surcharge` but fails the checks that need code.
- No case covers step 5's third stop condition: the user asks for a minimal change and the rewrite touches far more lines.
- There is no case where the right answer is **hybrid**.
- `clean-keep`'s `kept-pipeline` regex matches one literal line. It fails a cosmetic `.decode("ascii")` and passes a self-described fresh rewrite that kept that line. `says-old-won` is the real check.
- `finance-export`'s code traps only bite an agent that reaches for `csv.writer` or `.get(key, default)`. An agent that copies the old behavior passes them without ever finding the consumer.
- `max-length` and `daily-unchanged` also ask the judge to work out outputs by reading the code. They have been 6/6 so far, but they are the same kind of check that made `weekly` fail. If one fails, run the agent's code before trusting the verdict. `--keep-temp` seals the working directory, but `out/trace.jsonl` has every Write, Edit and Bash call. Agents often write code through a Bash heredoc into `$TMPDIR` and then `cp` it.
