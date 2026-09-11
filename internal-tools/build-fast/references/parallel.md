# Parallel builds

Load this only after the gate in step 2 passes. If you are here without checking the gate,
go back — most builds are solo.

## Four patterns worth spawning for

| Pattern | Split | Use when |
| --- | --- | --- |
| **Pipeline** | fetch/parse │ compute │ render | each stage is chunky on its own; pin the intermediate format verbatim in both prompts |
| **Deliverable** | one agent per asked-for thing (the script │ the chart) | each thing is its own substantial file, not two functions you would write in the same sitting; they share only the input file |
| **Race** | same brief, two approaches (library A │ library B, API │ scrape) | you genuinely don't know which will work; keep whichever runs on the real input first, drop the other |
| **Prep** | one agent readies the real input while you build against its shape | the input needs downloading, extracting, or credentials; pin the shape up front |

Two asked-for things is not by itself a reason to spawn. A script plus a chart, both short,
is faster written solo than briefed out. The Deliverable split pays only when each half
would be a real build on its own.

Race only on real uncertainty. Racing two variants of something you already know how to
write is pure waste.

## Every agent prompt, verbatim

- absolute paths in and out, the real input format, one real sample row
- the exact output contract, and "do not touch `<other files>` — another agent owns them"
- "no generality and no config layers; put whatever changes between runs in a CONFIG
  block at the top; let it crash on bad input"
- "run it on the real input before handing back; return the output file path, the actual
  output, and one line on anything you had to guess"

## Models

Pass `model` explicitly on every spawn — inheriting is the silent failure. Default
`sonnet`; `opus` for the piece with real uncertainty; `haiku` for mechanical work.

## No worktrees

Give each agent its own file path in one scratch directory. Pieces in separate files rarely
collide, and git ceremony is the exact overhead this skill exists to avoid. If the work
lands in a real repo and touches shared tracked files, this is the wrong skill — use
`worktree-swarm`.

## You integrate

Each agent ran only its own half, so run the pieces together on the real input yourself
before believing any of it. If you are blocked on a piece you could write in three minutes,
write it and drop the agent's version.
