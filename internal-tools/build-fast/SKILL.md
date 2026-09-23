---
name: build-fast
description: Manual-only prototype build, invoked with /build-fast. Gets a working first-draft script into the user's hands as fast as possible — the one or two things asked, output that satisfies the need, refine later.
argument-hint: "[what to build]"
effort: medium
disable-model-invocation: true
---

# Build Fast

The point is speed: a working script in the user's hands as fast as possible — the one or
two things asked, run on the real input, handed over as a first draft. Anything off the
fastest path to a correct working script is waste, and making it nice is waste.

Correct is not the exception to that. A wrong script is the slowest outcome available:
the user acts on bad output, finds out days later, and the whole thing gets rebuilt with
trust spent. Rough, narrow and ugly are all fine; wrong is not, because nothing downstream
will catch it. The draft is in the code, never in the answer.

The time comes from cutting scaffolding and generality — other users, other input shapes,
config layers, extension points, anything for a future nobody has asked for. What stays is
whatever makes this script right every time the user re-runs it. Refinement is a separate
pass the user asks for once they know more, not something you fold in now because you can
already see where it would go.

Wrong skill if it has to ship as production code now, or if the user wants the refined
version rather than a first pass: say so and build it properly instead. Wrong skill too if
it is a one-off you could do by hand in ten minutes — do that and hand back the answer,
because a script nobody re-runs is pure overhead.

## Where the time actually goes

Not typing. These are what make a fast build slow:

- **Deciding.** Weighing two libraries that both work, naming things well, choosing a
  structure. Take the one you know best and move — at this size no choice is expensive
  to undo.
- **Reading.** Skimming a whole codebase or a full API doc before writing a line. Read
  the one signature you need.
- **Building it general, then narrowing.** Write the specific thing. It is shorter, and
  it is what was asked for.

## 1. Lock the scope

No interview. Write one line: what the script does, what it produces, and how you will
know the output is right. "Reads orders.json, writes a CSV of every order over $500,
prints the total. Check: order #4417 by hand against the source."

- One or two things. A want that shows up mid-build is a new request: name it at handoff
  and leave it unbuilt.
- Ask at most one question, and only when a wrong guess wastes the whole build — which
  real input file, or which of two incompatible output formats. Every question is a round
  trip through the user, so otherwise take the obvious default, say so in one line, and
  build.
- Everything outside that line is out, including things that would obviously be nice.

Name the check now, before any output exists — a check chosen after seeing the output is
the one the output already passes. It has to come from outside the program, because the
script's own printout is not evidence about itself:

- **spot-check** — open the source, find one record by hand, compare it against the output
- **count** — compare against something the script did not produce, like `wc -l` on the
  input, a figure the user gave you, or your own count of the source rows. Printing rows-in
  and rows-out and seeing them match is the script agreeing with itself.
- **invariant** — no nulls in the key column, dates inside the expected range, parts sum
  to a total you got independently
- **look at it** — for a chart, page, or image, actually open it

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
JS inline, opened with a double-click; give it browser defaults plus only the CSS it needs
to be readable, with no palette, web fonts, or design pass. If it needs a server because it
touches a database or a key, one file of whatever the repo already uses.

Before reaching for any library, walk down this list and stop at the first rung that
holds. Most fast builds never get past the third.

1. **Skip it.** The script does not need the capability — a progress bar, a retry layer, a
   cache. Leave it out and say so in one line.
2. **Already here.** The repo has the helper, the client, the parser. Look before you
   write, because re-implementing what sits two files over is the commonest waste.
3. **Stdlib, or the platform.** `csv`, `json`, `sqlite3`, `argparse` on the Python side. In
   a browser the platform is the bigger half — `<input type="date">` over a picker library,
   `<details>` over an accordion, a plain `<table>` over a grid, CSS grid over a layout
   engine, `fetch` over a request library.
4. **Already installed.** A package in the environment, or one the repo already imports.
5. **A new dependency, last.** Only when it saves real work that the rungs above cannot —
   a parser for a genuinely hard format, a charting library. One `<script src>` from a
   CDN, or one `pip install` into whatever Python environment is already active. If pip
   refuses with `externally-managed-environment`, don't pass `--break-system-packages`,
   because that writes into the system Python. Use `uv run --with <pkg>` if `uv` is on
   PATH, otherwise one `.venv` beside the script, and put the exact command in the `run:`
   header line. Name what you added and why.

The build step stays cut at every rung. No venv beyond that fallback, no lockfile, no
`requirements.txt`, no `package.json`, no bundler, no `create-*` scaffold.

Cut:

- polish and refactor passes — renaming, extracting helpers, tidying as you go. Ugly and
  correct ships, and the first version that works is the version you hand over.
- tests as a suite, mocks, fixtures, CI
- config files, env layers, a flag for every behaviour. One `CONFIG` block at the top or
  a single positional argument covers the one or two things that actually vary. Constants
  the task defines — the endpoint, the column names, the threshold — stay hardcoded. Keys
  and tokens are the exception and never go in the block; read them from the environment,
  and name the variable in the `assumes:` header line.
- error handling that recovers. A `try/except` that returns a default turns a visible crash
  into a plausible wrong answer, so let it crash. Allow exactly two catches: a check at the
  top that exits with a message naming the missing or unreadable input (`no such input:
  data.csv`, not a bare `KeyError` on line 40, because they run this without you), and a
  per-record catch that counts the failures and reports the count at the end. Neither one
  may substitute a value for the thing that failed.
- packaging, README, docstrings, type ceremony, logging frameworks — `print` is the logger
- generality: one input shape, one output shape
- performance work, unless the thing will not finish otherwise

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

Put it beside the data it works on, or in the repo it belongs to, unless the user named
somewhere else. Don't ask; a script left in a temp directory is one they will rewrite from
memory next month.

Open the file with three comment lines, no more, in whatever comment syntax the language
uses, because they come back to this cold:

```
# first draft: <what it does>
# run: <the exact command, or "open in a browser">
# assumes: <input shape, env vars, and anything else baked in>
```

## 4. Run it, check the output once

Run it once on the real input, then run the check you named in step 1 — that one, not
whichever looks cheapest now, because the cheapest-looking check is the one this output
happens to pass. It is one check, not a test suite. It costs a minute, and skipping it
because the code looks obviously right risks the whole rebuild.

Write a real assert, or cache an intermediate, only when it makes the build *faster* — when
the tricky bit needs iterating and re-running the whole pipeline each time costs more than
a five-line check. That is the only way a test earns its place here.

If the run itself is destructive — it overwrites, deletes, moves, posts, or sends — do
not point it at the real thing first. Copy the input aside and run against the copy, or
add a dry-run that prints what it would do and show that output before the real run.
The draft is in the code, never in the user's data.

If the check fails, fix it and re-run before reporting. Never hand over a script you have
not run: they will trust it on inputs you never saw.

## 5. Hand back

In this order:

1. **The script and the exact command to run it.** That is the deliverable.
2. **The output from your run**, or where it landed — proof it works, and usually the
   thing they wanted to see first.
3. **What you checked and what it said**, one line: "spot-checked order #4417 against
   orders.json: amount and date match its CSV row."
4. **What is baked in and what you skipped**, two to four bullets: the input shape it
   assumes, what it does not handle, any rows dropped, what a later run can safely vary.
   Anything skipped and left unnamed gets trusted as done.

Say plainly that it is a first draft, and name in one line where a later pass would
start — the input handling, the edge case you skipped, the slow bit, the want you parked
in step 1. Then stop. Naming the seam is the handoff; working it is the next request, with
its own scope line.
