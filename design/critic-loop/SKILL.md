---
name: critic-loop
description: >
  Manual-only critic loop, invoked with /critic-loop. No reference: one builder works
  from the project's own context (code, design files, docs) and stays consistent with
  it, or builds from the request alone in an empty project. Fresh-context critics
  score each round, and the builder revises on their feedback until every critic
  clears a configurable score floor with no blocking issues, or the round cap is hit.
  Skip when the user has a real-world reference to match; that is design-loop.
disable-model-invocation: true
---

# Critic Loop

Five steps: intake, context, preflight, loop, handback. Do not build before the loop starts.

There is no reference and no `bar.md`. The standard is the project itself: what already exists sets the conventions, and the critics hold the builder to them. If the user names something to match, stop and suggest `/design-loop` instead.

## 1. Intake

Read the goal and the stop condition from the invocation. Accept flags or plain words ("until every critic gives 9, max 4 rounds").

| Setting | Flag | Default | Valid |
| --- | --- | --- | --- |
| Score floor | `--min-score N` | `8` | integer 0 to 10 |
| Round cap | `--max-rounds M` | `3` | integer, 1 or more |
| Critics | `--critics a,b,...` | `brief,consistency,craft` | one or more names |

The stop condition: **every critic scores at least N and reports zero blocking issues**, or M rounds have run. `--min-score 0` turns off the score check, so the loop stops only when there are no blocking issues left. The blocking check is never off. A score is not a pass while a critic still names something blocking.

Reject invalid values with the valid range and ask again. Do not round or clamp them. Warn once if M is above 5, because each round costs one builder and every critic, and a gap that survives five rounds is rarely closed by a sixth. Ask only if the goal is missing. Everything else has a default.

Echo the resolved config in one line before going on: goal, floor, cap, critics.

## 2. Context

Read the project before anyone builds. Look at existing code, components, tokens and theme files, design files, docs, READMEs, and any `design-system.md` or `CLAUDE.md` conventions. Then write `context.md` in the session scratchpad. It is run state, not a deliverable, so never write it into the project tree.

Write conventions as checkable lines with the file they came from. An adjective resolves to nothing, so a critic handed one just agrees with itself. A line with a value and a path resolves to yes or no:

- not "consistent styling", but "colours come from `src/theme/tokens.ts`; no raw hex in components"
- not "matches the existing UI", but "buttons are `<Button variant>` from `src/ui/Button.tsx`, never a bare `<button>`"
- not "same tone as the docs", but "docs use second person and imperative headings (`docs/guide.md`)"

Only write what the project actually does. A convention you inferred from one file is a guess, so say so on that line or leave it out. Scope follows the goal: list the conventions that the thing being built will touch, not the whole codebase.

**Empty project:** if there is nothing to be consistent with, skip `context.md`, drop the consistency critic, and say the build is greenfield from the request. Do not invent conventions to fill the gap. A consistency critic grading against made-up rules is grading noise.

Show `context.md` in one short block and continue. Do not wait for approval unless the user asked to review it.

## 3. Preflight

A check, not a question. Report it in one block:

- Confirm you can render the output: screenshots for UI, a filmstrip for motion, a PDF render for a document, the actual run output for a CLI or API. Capture a component at its own bounds, not inside a full-page shot. Without a render the craft critic goes blind.
- Record the starting commit (`git rev-parse HEAD`) as the diff base for the consistency critic, and note whether the tree was already dirty. With no git repo, the critic reads the files the builder lists instead.
- Name any generation tools the goal needs (image, voice, video) and confirm they are connected.

Print what works, what is missing, and **which critic goes blind**. Drop a blind critic and say so. Never run it on a guess. If every critic would be dropped, stop and tell the user. A loop with no one judging is a single build.

## 4. Loop

One builder, one or more critics, every round:

1. The builder builds or revises, working in place on the project files.
2. Every critic judges the current state in parallel, each with fresh context.
3. If every critic passes, stop. Otherwise the feedback goes back to the builder and the next round starts.

Run this as a workflow. Invoking `/critic-loop` is itself the opt-in that authorizes it, so do not make the user type "ultracode" first. Read `references/workflow.md` for the script, the schema, and the failure modes.

### Critics

Write each critic's brief for this run. "Does it do the job" means something different for an animation than for a settings page, so do not reuse generic wording across goals.

| Critic | Judges against | Sees | Model | Why |
| --- | --- | --- | --- | --- |
| **Brief** | The user's request only, ignoring aesthetics | rendered output | `sonnet` | Simple judgment |
| **Consistency** | `context.md` only | rendered output **and the diff** | `sonnet` | Reusing a component, token, or pattern is a property of the code, so this is the one critic allowed to read it |
| **Craft** | Its own expert eye for the medium | rendered output only, never code | `opus` | **Never downgrade.** A cheap craft critic passes everything and the loop ends on round one. |

Any other name in `--critics` (for example `a11y`, `perf`, `copy`) becomes an extra critic. Write a brief for that lens and run it on `sonnet`, rendered output only, unless the lens is inherently about code. Pass `model` explicitly on every critic. Inheriting the parent model either overpays for simple checks or, under a cheap parent, blinds the craft critic. If these model names are gone, map them by the Why column.

### Scores without drift

Scores drift upward when a critic grades against its own last score. These are the countermeasures, and the script enforces all of them:

- Critics never see earlier rounds: no prior scores, no gap history, no builder summary. They get the files changed and how to render them. Each round is judged cold.
- One anchored rubric for every critic:
  - 10: nothing a demanding expert would change
  - 8: shippable, only nits left
  - 6: works, but an expert would send it back
  - 4: major problems
  - 2: misses the goal or is broken
- Blocking issues are listed separately from the score, and any blocking issue fails the critic whatever its score.
- Critics are harsh. Praise is not useful.

### Feedback to the builder

The builder gets every blocking issue from every failing critic, ranked brief first, then consistency, then the rest, with craft last. If it does not do the job, nothing else matters yet. Each critic still under the floor also contributes its single biggest gap. Fix in that order. A critic that passed adds nothing. The builder also gets its own previous summary, so it knows what it already tried. That summary goes to the builder only, never to a critic.

A critic that errored or returned nothing is not a pass. It blocks the round until it reports.

`--max-rounds` is a budget ceiling, not a target. The exit is passing. Running out of rounds is reported as unresolved, never as a quiet pass.

## 5. Handback

On a pass, report the round it passed on, each critic's final score, and the files changed.

On hitting the cap, report:

- each failing critic, its last score, and its last blocking issues in its own words
- the score history per critic, so a plateau is visible
- any blocking issue that came back in near-identical words every round
- what you would try next, in one line

A blocking issue that comes back verbatim usually does not mean the work is hard. It means the builder cannot close it from where it stands. Check these causes in order:

- **`context.md` is wrong or contradicts itself.** The consistency critic is enforcing a convention the project does not actually follow, or two that conflict. Fix `context.md`.
- **The fix is outside the builder's medium.** It needs an asset or a tool it was not given. Change the builder's inputs.
- **The floor is above what the critic will give.** The critic lists no blocking issues but stays at 7 every round against a floor of 8. Say so; the user may lower the floor or accept the result.

Say which one you think it is. Raising the round cap is almost never the fix.

## What breaks this

- A thin `context.md`, full of adjectives instead of lines a critic can check, so the consistency critic agrees with itself.
- Inventing conventions for an empty project.
- The builder judging its own work. Critics need fresh context.
- Showing critics their earlier scores. Drift follows.
- Letting a high score override a blocking issue.
- Treating the round cap as a target, or quietly passing work that ran out of rounds.
