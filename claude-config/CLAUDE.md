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

1. **Re-run the acceptance and the whole suite on the current revision.** Quote the final lines and the exit code. Don't skip, xfail or loosen tests to get green.
2. **Capture the command's own exit code.** After a pipe, `$?` belongs to the last command; use `set -o pipefail` or `${PIPESTATUS[0]}`.
3. **No tests ran is a failure.** That includes pytest exit 5, a `-k` that matched nothing, and an all-skipped suite (which exits 0). Read the counts.
4. **Unknown is not pass.** Report a check that couldn't run as "not run", with the reason and where you looked. If the repo has no test suite, report tests as "not run: no suite" and give the build and lint results instead.

## When you report

5. **Inspect the artefact, not a summary of it.** Open the diff, decode the image, load the page and look at it, run the binary. "Saved", a 200 or a subagent's report is not proof; check the evidence behind it.
6. **Verify every citation.** `git cat-file -e <sha>^{commit}` and `git cat-file -e <rev>:<path>`; for "it's on main", `git fetch && git merge-base --is-ancestor <sha> origin/main`.
7. **State the base you tested, and re-check origin/main just before reporting.**

End every non-trivial run with three headings, in this order:

- **Blocked on me:** decisions or approvals you need from me, or "nothing".
- **Changed:** what you did, and the call sites if it was a fix.
- **Evidence:** base sha · acceptance command, exit code and output · suite counts · each CI job's status · what wasn't run, and why · artefacts you opened.
