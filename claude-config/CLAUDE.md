## Before starting
For non-trivial tasks, restate the goal and your plan in a few lines. If anything is ambiguous, ask and wait. Otherwise, proceed.

## Autonomy
Continue without asking when a step doesn't need my input. Stop and ask only when:
- you can't continue without me, or
- the action is destructive or hard to reverse: deleting files or data, discarding uncommitted changes (`git reset --hard`, `git checkout -- .`, `git clean`), force-pushing, rewriting history, pushing to a remote, or changing anything outside this repository.
- If you really stop and ask, put any questions for me under a **Needs your input** heading at the end of your message.

## Testing
Write tests first for code changes. Skip test-first for docs, comments, and config values.

## Commits
In a Git repository, commit at logical checkpoints without asking, only when tests pass. If no test suite exists, commit when the code builds and lints cleanly. Stage only files related to the change. Use concise commit messages.