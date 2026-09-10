---
name: build-fast
description: >
  Build a deliberately disposable program or script that does the one or two things
  asked and nothing else, run it on the real input, and hand back the output. Use when
  the user says "quick script", "one-off", "throwaway", "quick and dirty", "hack
  something together", "don't over-engineer it", "no tests needed", or when they want a
  specific output — a number, a file, a chart, a converted dataset — and the program is
  only the means to get it. Splits into parallel worker agents when the build has a
  clean seam and is big enough to be worth the spawn.
  Skip when the code will be maintained, extended, reused, or read by other people; when
  it ships as production code; when the user asks for tests, robustness, or a design;
  and when a wrong output would be costly and nobody would catch it — verify properly
  there instead. For multi-file work inside an existing codebase, use worktree-swarm.
---

# Build Fast

Build the smallest thing that produces the asked-for output, run it, hand back the
output. The program is a receipt, not a deliverable — it gets thrown away.

Fast means cutting scaffolding, not correctness. Everything serving a *future* — reuse,
config, other inputs, other users, a second run — is out. Everything serving *this
output being right* stays in. A plausible wrong answer delivered fast is the only real
failure mode here, because nothing downstream will catch it.

## 1. Lock the scope

No interview. Write one line: the deliverable and the shape it lands in. "A CSV of every
order over $500 in orders.json, plus the total."

- One or two things. A third want that appears mid-build waits until the first two are
  built and running.
- Ask exactly one question, and only when a wrong guess wastes the whole build — which
  real input file, or which of two incompatible output formats. Otherwise take the
  obvious default, say so in one line, and build.
- Everything outside that line is out, including things that would obviously be nice.

## 2. Solo or parallel

Spawn workers only when all three hold:

- the build is 2+ pieces, each a real chunk of work — or one piece is slow waiting on a
  download, a scrape, a render
- each piece owns its own file, and the seam between them is something you can pin
  verbatim: an exact JSON shape with a real sample row, a function signature, a file
  path plus format
- you can write each prompt self-contained without re-deriving the whole task

Otherwise build it solo. **For one script under a couple hundred lines, spawning is
slower than writing it** — the prompt and the integration cost more than the build.

Four patterns worth spawning for:

| Pattern | Split | Use when |
| --- | --- | --- |
| **Pipeline** | fetch/parse │ compute │ render | each stage is chunky; pin the intermediate format verbatim in both prompts |
| **Deliverable** | one agent per asked-for thing (the script │ the chart) | the user asked for two things; cleanest seam there is, they share only the input file |
| **Race** | same brief, two approaches (library A │ library B, API │ scrape) | you genuinely don't know which will work; keep whichever runs on the real input first, drop the other |
| **Prep** | one agent readies the real input while you build against its shape | the input needs downloading, extracting, or credentials; pin the shape up front |

Race only on real uncertainty. Racing two variants of something you already know how to
write is pure waste.

Put this in every agent prompt, verbatim:

- absolute paths in and out, the real input format, one real sample row
- the exact output contract, and "do not touch `<other files>` — another agent owns them"
- "hardcode paths and constants, do not generalize, let it crash on bad input"
- "run it on the real input before handing back; return the output file path, the actual
  output, and one line on anything you had to guess"

Pass `model` explicitly on every spawn — inheriting is the silent failure. Default
`sonnet`; `opus` for the piece with real uncertainty; `haiku` for mechanical work.

Skip worktrees. Give each agent its own file path in one scratch directory: disposable
pieces rarely collide, and git ceremony is the exact overhead this skill exists to
avoid. If the work lands in a real repo and touches shared tracked files, this is the
wrong skill — use `worktree-swarm`.

You integrate. Each agent ran only its own half, so run the pieces together on the real
input yourself before believing any of it. And if you are blocked on a piece you could
write in three minutes, write it and drop the agent's version.

## 3. Build

Cut, always:

- tests as a suite, mocks, fixtures, CI
- config, flags, CLI args, env layers — hardcode paths and constants in one block at the
  top where they are easy to find and change
- error handling that recovers. A `try/except` returning a default is the most dangerous
  line in a throwaway: it converts a visible crash into a plausible wrong answer. Let it
  crash.
- packaging, README, docstrings, type ceremony, logging frameworks — `print` is the logger
- generality: one input shape, one output shape, one run
- performance work, unless the thing will not finish otherwise
- refactor passes. Ugly and correct ships.

Never cut:

- **the real input.** A toy sample proves nothing about the actual file. If the real data
  is not available yet, say so and build against a real sample of it, never an invented one.
- **all of the data.** No silent truncation, no dropped tail, no skipping rows that fail
  to parse — if rows get dropped, count them and report the count.
- **the actual hard part.** A merged cell, a timezone, pagination, an encoding: that *is*
  the task. Approximating it is not fast, it is not doing the job.
- **the user's stated constraints.**
- **arithmetic and units.** Nothing downstream catches a wrong number.

Write it outside the project tree — a scratch or temp directory — unless the user asked
for it in the repo. A throwaway committed to a repo stops being a throwaway.

Give the file one comment on its first line, no more:
`# throwaway: <task>. hardcoded for <input>. not for reuse.`

## 4. Run it, check the output once

Minimal test means one real run plus **one correctness check that is not the program's
own word for it.** Take the cheapest that fits:

- **spot-check** — open the source, find one record by hand, compare it against the output
- **count** — rows in versus rows out, expected number of files, a total that must match
  a known figure
- **invariant** — no nulls in the key column, dates inside the expected range, parts sum
  to the whole
- **look at it** — for a chart, page, or image, actually open it

That check is non-negotiable, and it is not a test suite. It exists because a plausible
wrong answer is invisible downstream, and being right is the entire point of the
deliverable.

Write a real assert only when it makes the build *faster* — when the tricky bit needs
iterating, and re-running the whole pipeline each time costs more than a five-line
check. That is the only way a test earns its place here.

If the run itself is destructive — it overwrites, deletes, moves, posts, or sends — do
not point it at the real thing first. Copy the input aside and run against the copy, or
add a dry-run that prints what it would do and show that output before the real run.
Disposable is about the code, never about the user's data.

If the check fails, fix it and re-run before reporting. Never hand over a script you have
not run.

## 5. Hand back

In this order:

1. **The output.** The number, the file, the chart — that is what was asked for. Lead
   with it; do not bury it under the implementation.
2. **What you checked and what it said**, one line: "spot-checked order #4417 against the
   source, matches; 1,204 rows in, 1,204 out."
3. **What is baked in**, two to four bullets: hardcoded paths, assumptions, what it does
   not handle, any rows dropped.
4. The script path, marked disposable.

If the user wants to keep or extend it, that is the moment it stops being disposable.
Name what would have to change — the hardcoded paths, the absent error handling, the
untested edges — and harden it if they say go. Never harden preemptively.

## What breaks this

- **Scope creep.** Two things means two. A third is a new request.
- **`try/except` with a fallback value.** Turns a crash nobody could miss into a wrong
  answer nobody sees.
- **A toy input.** Passing on invented data says nothing about the real file.
- **Skipping the one check** because the code obviously works. Obvious is where wrong
  answers live.
- **Spawning for a small build.** Three agents on a 60-line script is slower than typing it.
- **Handing over an unrun script.** The output is the deliverable; with no run there is
  no deliverable.
