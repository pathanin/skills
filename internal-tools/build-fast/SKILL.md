---
name: build-fast
description: Manual-only prototype build, invoked with /build-fast. Gets a working first-draft script into the user's hands as fast as possible — the one or two things asked, output that satisfies the need, refine later.
disable-model-invocation: true
---

# Build Fast

**The point is speed: a working script in the user's hands as fast as possible.**
Everything else here — the narrow scope, the missing scaffolding, the single check, the
deferred polish — is there to serve that. Anything off the fastest path to a correct
working script is waste, and making it nice is waste.

Correct is not the exception to that. A wrong script is the slowest outcome available:
the user acts on bad output, finds out days later, and the whole thing gets rebuilt with
trust spent. The draft is in the code, never in the answer — rough, narrow and ugly are
all fine, wrong is not, because nothing downstream will catch it.

So: the smallest script that does the one or two things asked, run on the real input,
handed over as a working first draft. The script is the deliverable, and its output has
to actually satisfy the need.

Think prototype. No architecture, no options nobody asked for, meant to be refined later
— and later is the point. Refinement is a separate pass the user asks for once they know
more, not something you fold in now because you can already see where it would go. They
keep this and re-run it, so anything that varies between runs still has to be changeable
without editing the code.

Cutting scaffolding is where the time comes from. Generality goes: other users, other
input shapes, config layers, extension points, anything for a future nobody has asked
for yet. What stays is whatever makes this script right every time it runs.

Wrong skill if it has to ship as production code now, or if the user wants the refined
version rather than a first pass. Say so and build it properly instead.

## Where the time actually goes

Not typing. These are what make a fast build slow:

- **Deciding.** Weighing two libraries that both work, naming things well, choosing a
  structure. Take the one you know best and move — at this size no choice is expensive
  to undo.
- **Reading.** Skimming a whole codebase or a full API doc before writing a line. Read
  the one signature you need.
- **Building it general, then narrowing.** Write the specific thing. It is shorter, and
  it is what was asked for.
- **Polishing mid-build.** Renaming, extracting helpers, tidying as you go. Ugly and
  correct ships.
- **Asking.** Every question is a round trip through the user. One question, only when a
  wrong guess wastes the build (step 1).
- **Going sequentially through pieces that had a clean seam** (step 2).
- **Debugging through the whole pipeline.** When testing the tricky bit means re-running
  everything, cut a fast inner loop first — a cached intermediate, a five-line assert.
  That is the one test that pays for itself (step 4).

## 1. Lock the scope

No interview. Write one line: what the script does and what it produces. "Reads
orders.json, writes a CSV of every order over $500, prints the total."

- One or two things. A third want that appears mid-build waits until the first two are
  built and running.
- Ask exactly one question, and only when a wrong guess wastes the whole build — which
  real input file, or which of two incompatible output formats. Otherwise take the
  obvious default, say so in one line, and build.
- Everything outside that line is out, including things that would obviously be nice.

## 2. Solo or parallel

Parallel work is a speed bet, and it loses more often than it looks. Spawn only when
all three hold:

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
- "no generality and no config layers; put whatever changes between runs in a CONFIG
  block at the top; let it crash on bad input"
- "run it on the real input before handing back; return the output file path, the actual
  output, and one line on anything you had to guess"

Pass `model` explicitly on every spawn — inheriting is the silent failure. Default
`sonnet`; `opus` for the piece with real uncertainty; `haiku` for mechanical work.

Skip worktrees. Give each agent its own file path in one scratch directory: pieces in
separate files rarely collide, and git ceremony is the exact overhead this skill exists to
avoid. If the work lands in a real repo and touches shared tracked files, this is the
wrong skill — use `worktree-swarm`.

You integrate. Each agent ran only its own half, so run the pieces together on the real
input yourself before believing any of it. And if you are blocked on a piece you could
write in three minutes, write it and drop the agent's version.

## 3. Build

Cut, always:

- tests as a suite, mocks, fixtures, CI
- config files, env layers, a flag for every behaviour. One `CONFIG` block at the top or
  a single positional argument covers the one or two things that actually vary. Constants
  the task defines — the endpoint, the column names, the threshold — stay hardcoded.
- error handling that recovers. A `try/except` returning a default is the most dangerous
  line in a script like this: it converts a visible crash into a plausible wrong answer.
  Let it crash.
- packaging, README, docstrings, type ceremony, logging frameworks — `print` is the logger
- generality: one input shape, one output shape
- performance work, unless the thing will not finish otherwise
- refactor passes. The first version that works is the version you hand over.

Never cut:

- **the real input.** A toy sample proves nothing about the actual file. If the real data
  is not available yet, say so and build against a real sample of it, never an invented one.
- **all of the data.** No silent truncation, no dropped tail, no skipping rows that fail
  to parse — if rows get dropped, count them and report the count.
- **the actual hard part.** A merged cell, a timezone, pagination, an encoding: that *is*
  the task. Approximating it is not fast, it is not doing the job.
- **the user's stated constraints.**
- **arithmetic and units.** Nothing downstream catches a wrong number.
- **whatever changes between runs.** The input path, the date range, the output name.
  Bury those in the source and re-running means editing code, which is what turns a
  working script into one the user rewrites from scratch instead.
- **a crash that names what to fix.** Still let it crash — but `no such input: data.csv`
  beats a bare `KeyError` on line 40. They run this without you there.

Put it where the user will find it again — beside the data it works on, or wherever they
keep scripts. Ask if that is not obvious. A script left in a temp directory is one they
will rewrite from memory next month.

Open the file with three comment lines, no more, because they come back to this cold:

```
# first draft: <what it does>
# run: python thing.py <input.csv>
# assumes: <input shape, and anything else baked in>
```

## 4. Run it, check the output once

Minimal test means one real run plus **one correctness check that is not the program's
own word for it.** Take the cheapest that fits:

- **spot-check** — open the source, find one record by hand, compare it against the output
- **count** — rows in versus rows out, expected number of files, a total that must match
  a known figure
- **invariant** — no nulls in the key column, dates inside the expected range, parts sum
  to the whole
- **look at it** — for a chart, page, or image, actually open it

That check is non-negotiable, and it is not a test suite. It costs a minute. Skipping it
risks the rebuild, which costs the entire build again plus whatever the user did with
the bad output in between — so the check is the fast move, not the careful one. A
plausible wrong answer is invisible downstream, and they will run this again on data you
never see.

Write a real assert only when it makes the build *faster* — when the tricky bit needs
iterating, and re-running the whole pipeline each time costs more than a five-line
check. That is the only way a test earns its place here.

If the run itself is destructive — it overwrites, deletes, moves, posts, or sends — do
not point it at the real thing first. Copy the input aside and run against the copy, or
add a dry-run that prints what it would do and show that output before the real run.
The draft is in the code, never in the user's data.

If the check fails, fix it and re-run before reporting. Never hand over a script you have
not run.

## 5. Hand back

In this order:

1. **The script and the exact command to run it.** That is the deliverable.
2. **The output from your run**, or where it landed — proof it works, and usually the
   thing they wanted to see first.
3. **What you checked and what it said**, one line: "spot-checked order #4417 against the
   source, matches; 1,204 rows in, 1,204 out."
4. **What is baked in and what you skipped**, two to four bullets: the input shape it
   assumes, what it does not handle, any rows dropped, what a later run can safely vary.

Say plainly that it is a first draft, and name in one line where a later pass would
start — the input handling, the edge case you skipped, the slow bit. Then stop. Naming
the seam is the handoff; working it is the next request, with its own scope line.

## What breaks this

- **Scope creep.** Two things means two. A third is a new request.
- **`try/except` with a fallback value.** Turns a crash nobody could miss into a wrong
  answer nobody sees.
- **A toy input.** Passing on invented data says nothing about the real file.
- **Hardcoding what varies.** If re-running it means editing the source, it is not a
  script the user keeps.
- **Skipping the one check** because the code obviously works. Obvious is where wrong
  answers live.
- **Quietly polishing.** Refinement is the next pass, and asking for it is the user's call.
- **Handing a draft over as finished.** Name what you skipped, or it gets trusted as done.
- **Spawning for a small build.** Three agents on a 60-line script is slower than typing it.
- **Handing over an unrun script.** They will trust it on inputs you never saw. Unrun,
  it is a guess with a filename.
