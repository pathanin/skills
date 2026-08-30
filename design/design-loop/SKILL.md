---
name: design-loop
description: >
  Manual-only design loop, invoked with /design-loop. Takes a goal and a real-world
  reference, tears the reference into checkable mechanisms, then loops a builder
  against three fresh-context critics (brief, system, craft) per piece until all
  three agree ours wins. Works at any size, from a whole site down to one button's
  toggle animation; costs more than a single build either way, so it pays off only
  when there is a specific bar to clear.
disable-model-invocation: true
---

# Design Loop

Four phases: interview, preflight, teardown, loop. Do not skip ahead. Do not start building during phases 1 to 3.

## Phase 1: Interview

Ask these, together, then stop and wait.

1. What are you building, and how long or how big? Drop the "how long or how big" when the goal is already one component — a toggle animation, a single card, one endpoint's error messages. The size is not in question there, and asking makes the run feel heavier than the work is.
2. Name something that already does this brilliantly. A site, a video, a doc, anything I can open. If nothing comes to mind, say skip.
3. Any files I should work from? Design system, brand doc, script, existing draft.

If they name something vague ("Apple's website", "good SaaS design"), push once for the specific page or file. The test is not whether the bar is famous or tasteful, it is whether a critic can open it and hold our work up against it. A vague bar is the number one reason this method fails: the critic invents a comparison and approves everything on round one.

If they say skip on question 2, propose three candidate bars, one line each on why, and wait. If they do not answer, take the hardest one.

A small goal usually has an *easier* bar than a large one, not a harder one. "Apple's website" is vague; "the like button on this specific page" is a thing a critic can open and watch. When the scope is one component, push for the exact interaction, screen region, or numeric spec — those exist far more often than a whole reference site does, so reach for the skip branch later here, not sooner.

Not every goal has an artefact to point at. When it is a CLI, an API, an essay, a data pipeline, ask what plays the same role here that a screenshot of the real product plays for something built to imitate it. Usually one of three: a competitor's actual output, a spec or standard the result has to satisfy, or a measurement with a number on it. A bar can be a measurement. It cannot be a mood.

## Phase 2: Preflight

A check, not a question. Run it before any work and report in one block.

- Fetch the bar now. Screenshot the URL or read the file. If it is blocked or missing, say so and ask for another.
- Confirm you can render our output: screenshots for a site, a filmstrip of frames for animation, a PDF render for a doc. No render means no craft critic.
- Small scope does not relax this — it tightens it. A 300ms toggle *is* its filmstrip, and a component shot inside a full-page capture is a few pixels in a field of empty ground. Confirm now that you can capture the component at its own bounds, and animation frame by frame, or the craft critic is grading whitespace you did not design.
- Name any generation tools the goal needs (image, video, voice) and confirm they are connected.
- Confirm the input files exist: design-system.md, brand doc, script.

Then print: what is working, what is missing, and **which critic goes blind** if something is missing. Never carry on quietly with a critic that cannot see.

## Phase 3: Teardown

Read the reference properly and write the mechanisms to `bar.md`. Count follows scope: 5 to 7 for a full build, 3 to 4 for a single component. Write the ones that are actually there — padding the list with mechanisms the reference does not exhibit gives the critic something unfalsifiable to grade.

This is the step that does the real work, and the step people get wrong. Adjectives are unfalsifiable, so a critic handed one just agrees with itself. Measurements are falsifiable, so a critic handed one has to go and look.

Useless, because two people can read them opposite ways:

- feels premium
- clean and modern
- good use of whitespace
- strong visual hierarchy

Checkable, because they resolve to a yes or a no:

- headline is 5x body size, three type sizes total
- one accent colour, used at most twice per screen
- motion always resolves in one direction
- nothing animates for under 400ms
- whitespace above the fold is at least 40% of the frame

Those examples are visual because references often are, but nothing about a mechanism requires it. For a CLI: every error names the file and the fix. For an API: no useful result takes more than one round trip. For prose: no sentence hedges twice. The test does not change — can a critic settle it by looking at the output, without knowing what we intended.

Every line must be something a critic can check by looking.

Three is the floor, and it is a floor on *checkable* lines, not on ambition — a small goal that yields three real mechanisms runs the loop exactly like a large one. Only when the reference genuinely offers fewer than three is there nothing for a critic to settle; say so and build it in a single pass instead.

Show `bar.md` to the user before continuing.

## Phase 4: Loop

Split the goal into the smallest pieces that can be improved and judged on their own. You choose the pieces. Keep it to three or four unless told otherwise, because every extra piece multiplies the run.

When the goal is already one piece — one component, one animation, one error message set — the piece list has one entry and you do not invent seams to fill it. Splitting a toggle into "the motion" and "the colour change" gives two builders one file and two critics half a thing to judge. Everything else runs unchanged: one piece cycling rounds against three critics is the whole method, and at that size it is cheap.

Then assign each mechanism in `bar.md` to the pieces it applies to, and hand each critic only its piece's mechanisms. `bar.md` describes the whole artefact; a piece is a part of it. A critic handed the full list marks a piece down for work that belongs to another piece — and because the builder cannot fix it without leaving its own brief, that failure repeats every round and burns the piece to exhaustion. Every mechanism should land on at least one piece; one that lands on none is a mechanism nothing is building toward, which is worth knowing before you start.

For each piece: fan out a builder, then three critics, each with fresh context and no knowledge of how the builder worked.

Run this as a workflow rather than by hand — in a script the rules below stop being things you have to remember and become structure the tool layer enforces. Invoking `/design-loop` is itself the opt-in that authorizes it, so do not make the user type "ultracode" first. Read `references/workflow.md` for the script, the schema, and the failure modes.

Rounds are the outer loop and every piece moves through them together: build all pieces, merge, then critique. Between building and critiquing, one agent reconciles what every builder produced — builders are blind to each other by design, and the merge agent pays the cost of that blindness once instead of every round. It reconciles the shared surface in place and returns a short **settled** note, the decisions now fixed across pieces, which goes into every builder's prompt next round. That note is the only channel between builders; keeping it that narrow is what preserves fresh context while killing the divergence.

The merged state is that round's build for every piece. Critics judge it, and any gap routes back to that piece's builder, which now sees the merged state. Skip the merge entirely when there is only one piece.

You never invent a critic. The three roles below are fixed so they cannot converge into the same opinion — but you write each one's brief per run, because "does it hit the brief" means something different for an animation than for a pricing page. Do not reuse generic wording across different goals.

| Critic | Judges against | Model | Why |
| --- | --- | --- | --- |
| **Brief** | The stated goal only, ignoring aesthetics | `sonnet` | Simple judgment, no vision needed |
| **System** | `design-system.md` only | `haiku` | Mechanical adherence checking |
| **Craft** | `bar.md` and rendered frames, never the code | `opus` | **Never downgrade this one.** A cheap craft critic approves everything and the loop dies on round one. |

Pass `model` explicitly on every critic spawn. Inheriting the parent model is the common silent failure: it pays top rates for the mechanical checks, and if the parent is cheap it quietly blinds the craft critic. If these model names are gone by the time you read this, map by the Why column rather than guessing at the names.

The craft critic puts ours next to the reference blind, labels stripped, says which is better, and names the single biggest gap.

If a critic has nothing real to judge against — no design system exists, or the output cannot be rendered — say so in preflight and run without it. Two honest critics beat three where one is inventing a standard so it has something to say.

Rules:
- Critics are harsh. Praise is not useful.
- Critics judge rendered output, never the code. Reading the implementation makes a critic evaluate intent instead of result.
- Binary verdicts, not scores. Scores drift upward every round.
- Every critic you ran must pass. Any fail goes back to the builder with the single biggest gap named. A critic that errored or was skipped is not a pass — it blocks the piece until it reports.
- Three rounds per piece, maximum. This is a budget ceiling, not a target: the exit is still winning, or the user stopping the run. A piece that hits the ceiling returns as unresolved with its gap history, never as a quiet pass.
- At three rounds the builder gets roughly two real correction opportunities, so one gap per round is now binding rather than free. Send the single biggest gap as the thing to fix, and list any other failing critics' gaps beneath it as do-not-regress lines. Do not let those become a second brief.

Keep a live progress page updating as work evolves: piece status, each critic's verdict, gap history, round count. The workflow tree in `/workflows` shows which agents are running right now, which is a different question — it does not carry the gap history, and that history is the thing worth watching, because a gap that keeps coming back means the builder cannot see what the critic sees.

## Handing back

A piece that does not win in three rounds is a normal outcome, not a failure to hide. Report per unresolved piece:

- which critic is still failing and its exact last gap, in the critic's words
- whether that critic failed **every** round — suggestive at three rounds rather than diagnostic, but still the first thing to look at
- the gap history, so a recurring gap is visible as recurring
- what you would try next, in one line

A critic that failed all three rounds may just be noise at that count — but when the same gap comes back verbatim each round, it usually does not mean the piece is hard. It means the builder cannot close that gap from where it stands. Three causes, in the order worth checking:

- **The mechanism belongs to another piece.** The critic is grading this piece on work the brief told the builder not to do. Fix the scoping, not the piece.
- **The gap does not exist in the medium the builder is working in.** It was asked for a photograph and given only CSS. Change the builder's inputs.
- **The mechanism was never checkable.** It slipped through teardown as an adjective. Fix `bar.md`.

Say which of the three you think it is. Raising the round count is almost never the fix.

## What breaks this

- A vague bar. By far the most common failure.
- The builder judging its own work. Critics need fresh context.
- A soft critic. Binary job, not a score.
- Treating the round cap as a target, or quietly passing a piece that ran out of rounds. The cap exists to bound cost; the exit is still winning.
- Over-specifying. Every extra instruction is one fewer decision the model makes with its own judgment.
