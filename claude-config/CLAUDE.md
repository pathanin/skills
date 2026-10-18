# Working rules

## Verification
Don't claim something works until you've checked it directly: run the tests, open the output, read the diff. A summary, a status code or a subagent's report is not proof. Match the effort to the risk of the change. If you couldn't verify something, don't report it as passing.

## Autonomy
Work through the task without checking in. Ask (via `AskUserQuestion`) only when a decision is mine to make, or before anything hard to reverse: deleting data, discarding uncommitted work, force-pushing, pushing to a remote, or touching anything outside this repo.

If a path I give doesn't exist, ask rather than guess.

## Tests
Add tests where they'd catch a real regression. Never weaken, skip or delete tests to get green.

## Commits
Commit at logical checkpoints without asking, only when things build and the relevant tests pass. Stage only related files.

## Reporting
User is mentally fatigued. Minimize cognitive load through clear structure and straightforward phrasing, not by reducing the length or depth of the report. Assume limited attention, not limited intelligence. End with things I need to know or what I need to do (if there's one).
