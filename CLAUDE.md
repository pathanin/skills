# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal collection of Claude Code **Skills** — no application code, no build/test/lint pipeline. Skills are grouped into three category directories: `design/`, `productivity/`, and `internal-tools/`. Each directory *inside* a category is one skill: a `SKILL.md` (instructions loaded into context when the skill triggers) plus, optionally, `scripts/`, `assets/`, and `references/` subdirectories the skill's instructions point to.

Categories are organizational only — plugin identity is the leaf directory name, which must match `name:` in both `SKILL.md` and `.claude-plugin/plugin.json`. Moving a skill between categories requires updating its `source` in `.claude-plugin/marketplace.json` to `./<category>/<skill>` (nested paths resolve fine), then commit + `claude plugin marketplace update local-skills` + `claude plugin update <name>@local-skills`.

See `README.md` for the current skill list and one-line descriptions — keep that table in sync when adding, renaming, moving, or removing a skill.

## Skill anatomy

Every `SKILL.md` starts with YAML frontmatter:

```yaml
---
name: skill-name          # matches the directory name
description: >            # the ONLY signal Claude uses to decide when to trigger this skill
  ...
---
```

The `description` is load-bearing: it's matched against the user's request to decide whether the skill fires at all, so it must state concrete trigger phrases *and* explicit skip conditions (see any existing `SKILL.md` for the pattern — e.g. `bump-homebrew`'s description lists both trigger phrasings and what to skip). When editing a skill, prefer tightening `description` over adding disclaimers in the body.

Supporting subdirectories, used inconsistently by design (each skill only has what it needs):
- `scripts/` — standalone Python invoked via `bash`/`python3` from the skill body. These are stdlib-only or declare their deps in prose inside `SKILL.md`, not in a `requirements.txt`.
- `assets/` — template files a script copies/edits rather than generates from scratch.
- `references/` — longer reference docs the skill body explicitly tells Claude to load only when needed, to avoid bloating the always-loaded `SKILL.md` (e.g. `design/tufte-viz/references/*.md`, `design/tufte-clarity/references/clarity-principles.md`).
- `.claude-plugin/plugin.json` — plugin manifest, present only on skills packaged as plugins; not a repo-wide convention.

## Working on a skill

- Treat `SKILL.md` as a prompt, not documentation — every sentence is an instruction to a future Claude instance, not an explanation for a human reader. Write imperatively, resolve ambiguity explicitly (numbered steps, exact command blocks, explicit stop/ask conditions), and avoid narrative filler.
- Several skills are process/interview skills with no code at all (`plan-relax`, `to-prd`, `dashboard-design`, `tufte-clarity`, `tufte-viz`). Changes to these are pure prompt-engineering: reread the whole file for internal consistency (numbered workflows, "when to stop/ask" rules, output contracts) rather than editing a section in isolation.
- `plan-relax` is deliberately low-pressure and hides progress from the user. Keep that tone when editing it — don't make it brisk or numbered, and don't add progress indicators or question counts.
- `tufte-clarity` and `tufte-viz` are siblings: `tufte-viz` is for actual data visualizations/charts, `tufte-clarity` generalizes the same principles to UI/web/slide design and explicitly cross-references `tufte-viz` for the data-viz-specific case. Keep the "Core Translation" table in `design/tufte-clarity/SKILL.md` in sync if Tufte concepts are added to `tufte-viz`.

## No build/lint/test commands

There is nothing to compile, lint, or test — skills are prompts, not code. Verify changes by reading the `SKILL.md` end to end for internal consistency.

Exception: a skill with an `evals/` directory has a `claude plugin eval` suite. Manual-only skills can't be reached by the no-plugin baseline, so run with `--ablation none` and compare against the previous version instead, e.g. `claude plugin eval . --runs 3 --ablation none --scaffold --trust-plugin --allow-tools Write Edit Bash` from the skill directory. Results land in `evals/results/`, which is gitignored.

Exception: `mods/` holds hook plugins (mods), which are code. Each has `*.test.tsx` files: run `claude plugin test mods/<name>` and `claude plugin validate mods/<name>` before committing a change to one.

# Working rules

"Done" is a claim that needs evidence. Scale the effort to the task: a one-line fix needs the checks under "Before you say done", not the full report.

## Before starting

For non-trivial tasks, restate the goal and your plan in a few lines. In the plan:

- **Write the acceptance command.** One command that passes only when the task is done. For docs or config, a build, a link check or a specific manual check also counts. Don't edit it later to make it pass; if it turns out to be wrong, change it and say so in your report.
- **Check that every path you were given exists.** If one doesn't, ask, rather than substituting a similar one.

If an ambiguity blocks the work, ask and wait. Otherwise, state your assumption in the plan and proceed.

## Autonomy

Continue without asking when a step doesn't need my input. Put status notes in the same message as your next action, rather than ending your turn to report. For long runs, keep the task list in `TASKS.md` and tick items off as you finish them.

Stop and ask only when:

- you can't continue without me, or
- the action is destructive or hard to reverse: deleting files or data, discarding uncommitted changes (`git reset --hard`, `git checkout -- .`, `git clean`), force-pushing, rewriting history, pushing to a remote, or changing anything outside this repository.

Never run a destructive command to answer a question; `git status` and `git diff` answer "does this match main". When you do need to ask, use `AskUserQuestion`.

## Testing

Write tests first for code changes. Skip test-first for docs, comments and config values.

- **Don't test a constant against itself.** Derive the expected value independently, or test both sides of the boundary.
- **Fix the class, not the instance.** Find every call site of the defect, and list them in your report.
- **Try a detector on a known-good and a known-bad case before trusting it.**
- **Register cleanup before the work** (`trap`, `finally`, `defer`), so it runs when the work fails.

## Commits

In a Git repository, commit at logical checkpoints without asking. A checkpoint commit needs the relevant tests to pass; if no test suite exists, the code must build and lint cleanly. Stage only files related to the change. Use concise commit messages.

## Before you say "done"

1. **Re-run the acceptance and the whole suite on the current revision.** Note the counts and the exit code. Don't skip, xfail or loosen tests to get green.
2. **Capture the command's own exit code.** After a pipe, `$?` belongs to the last command; use `set -o pipefail` or `${PIPESTATUS[0]}`.
3. **No tests ran is a failure.** That includes pytest exit 5, a `-k` that matched nothing, and an all-skipped suite (which exits 0). Read the counts.
4. **Unknown is not pass.** Report a check that couldn't run as "not run", with the reason and where you looked. If the repo has no test suite, report tests as "not run: no suite" and give the build and lint results instead.

## Before you claim anything

5. **Inspect the artefact, not a summary of it.** Open the diff, decode the image, load the page and look at it, run the binary. "Saved", a 200 or a subagent's report is not proof; check the evidence behind it.
6. **Verify every citation.** `git cat-file -e <sha>^{commit}` and `git cat-file -e <rev>:<path>`; for "it's on main", `git fetch && git merge-base --is-ancestor <sha> origin/main`.
7. **State the base you tested, and re-check origin/main just before reporting.**

## How to write the report

Write it like a message to a teammate: plain sentences, no headings or labels unless the run was long. Keep it as short as the task allows; a small fix needs a sentence or two.

- **Start with anything you need from me.** If there's nothing, skip it rather than saying so.
- **Then say what you changed and how you know it works**, in one line where you can. For example: "Tests pass on abc123 (142 passed, exit 0); CI is still running."
- **Mention what you couldn't check, and why.** One short line is enough.
- **Show command output only when it matters**, such as a failure or something unexpected. Otherwise the counts and exit code are enough.
