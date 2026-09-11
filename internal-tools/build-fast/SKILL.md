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
version rather than a first pass. Say so and build it properly instead. Wrong skill too if
it is a one-off you could just do by hand in ten minutes — do that and hand back the
answer, because a script nobody re-runs is pure overhead.

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
- Name the check now, in the same line — how you will know the output is right (step 4).
  Choosing it after you see the output means choosing the one the output already passes.

## 2. Solo or parallel

**Default solo. For one script under a couple hundred lines, spawning is slower than
writing it** — the prompt and the integration cost more than the build, and that covers
most of what this skill gets asked for. Two asked-for things is not a reason to spawn.

Parallel work is a speed bet, and it loses more often than it looks. Spawn only when all
three hold:

- the build splits into 2+ pieces, each one substantial enough that you would not write it
  in a single sitting — or one piece is slow waiting on a download, a scrape, a render
- each piece owns its own file, and the seam between them is something you can pin
  verbatim: an exact JSON shape with a real sample row, a function signature, a file
  path plus format
- you can write each prompt self-contained without re-deriving the whole task

If all three hold, read `references/parallel.md` for the split patterns, the agent prompt
contract, and the model rule. Otherwise build it solo and skip that file.

## 3. Build

Build the part that could sink it first — the merged cell, the pagination, the auth, the
encoding. If it turns out impossible you want that at minute two, not after the CSV writer
is finished and the shape of everything else depends on it.

The deliverable picks the language, and an existing codebase picks it outright. Data in,
file out is Python. Anything that has to run in a browser is one HTML file with the CSS and
JS inline, opened with a double-click — no server, no npm, no bundler, no framework. If it
needs a server because it touches a database or a key, one file of whatever the repo
already uses.

What stays cut in every language is the build step. No venv, no lockfile, no
`requirements.txt`, no `package.json`, no `create-*` scaffold. Reach for the standard
library first, and pull in a dependency only when it saves real work — a package already
installed, or a single `<script src>` from a CDN. Say which one you added and why.

Cut, always:

- tests as a suite, mocks, fixtures, CI
- config files, env layers, a flag for every behaviour. One `CONFIG` block at the top or
  a single positional argument covers the one or two things that actually vary. Constants
  the task defines — the endpoint, the column names, the threshold — stay hardcoded. Keys
  and tokens are the exception and never go in the block; read them from the environment,
  and name the variable in the `assumes:` header line.
- error handling that recovers. A `try/except` returning a default is the most dangerous
  line in a script like this, because it turns a visible crash into a plausible wrong
  answer. Let it crash. Exactly two catches are allowed, and nothing else: a check at the
  top that exits with a message naming the missing or unreadable input, and a per-record
  catch that counts the failures and reports the count at the end. Neither one may
  substitute a value for the thing that failed.
- packaging, README, docstrings, type ceremony, logging frameworks — `print` is the logger
- generality: one input shape, one output shape
- performance work, unless the thing will not finish otherwise
- refactor passes. The first version that works is the version you hand over.

Never cut:

- **the real input.** A toy sample proves nothing about the actual file. If the real data
  is not available yet, say so and build against a real sample of it, never an invented one.
- **all of the data.** No silent truncation, no dropped tail, no rows quietly skipped. If
  records can fail to parse, use the per-record catch above, count them, and print the
  count beside the output — a run that drops 40 of 1,200 rows has to say so.
- **the actual hard part.** A merged cell, a timezone, pagination, an encoding: that *is*
  the task. Approximating it is not fast, it is not doing the job.
- **the user's stated constraints.**
- **arithmetic and units.** Nothing downstream catches a wrong number.
- **whatever changes between runs.** The input path, the date range, the output name.
  Bury those in the source and re-running means editing code, which is what turns a
  working script into one the user rewrites from scratch instead.
- **a crash that names what to fix.** Still let it crash — but `no such input: data.csv`
  beats a bare `KeyError` on line 40. They run this without you there.

Put it beside the data it works on, or in the repo it belongs to, unless the user named
somewhere else. Don't ask — step 1 already spent the one question. A
script left in a temp directory is one they will rewrite from memory next month.

Open the file with three comment lines, no more, in whatever comment syntax the language
uses, because they come back to this cold:

```
# first draft: <what it does>
# run: <the exact command, or "open in a browser">
# assumes: <input shape, env vars, and anything else baked in>
```

## 4. Run it, check the output once

Minimal test means one real run plus the check you named in step 1. That commitment is
binding — you do not re-pick here, because the check that looks cheapest now is the one
this output happens to pass.

Whatever the check is, it has to come from outside the program. The script's own printout
is not evidence about itself:

- **spot-check** — open the source, find one record by hand, compare it against the output
- **count** — compare against something the script did not produce, like `wc -l` on the
  input, a figure the user gave you, or your own count of the source rows. Printing rows-in
  and rows-out and seeing them match is the script agreeing with itself, which proves
  nothing.
- **invariant** — no nulls in the key column, dates inside the expected range, parts sum
  to a total you got independently
- **look at it** — for a chart, page, or image, actually open it

That check is non-negotiable, and it is not a test suite. It costs a minute, and skipping
it risks the whole rebuild.

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
   source, matches; `wc -l` says 1,204 input rows, output has 1,204."
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
