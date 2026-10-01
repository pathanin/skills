---
name: critic-loop
description: >
  Manual-only critic loop, invoked with /critic-loop. No reference: one builder works
  from the project's own context (code, design files, docs) and stays consistent with
  it, or builds from the request alone in an empty project. Fresh-context critics
  judge each round, and the builder revises on their feedback until no critic has a
  blocking issue and every scored critic clears a configurable floor, or the round
  cap is hit.
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
| Score floor (scored critics only) | `--min-score N` | `8` | integer 0 to 10 |
| Round cap | `--max-rounds M` | `3` | integer, 1 or more |
| Critics | `--critics a,b,...` | `brief,consistency,craft` | one or more names |

The stop condition: **no critic reports a blocking issue, and every scored critic scores at least N**, or M rounds have run. Brief and consistency are pass/fail, so the floor applies only to craft and to extra critics that judge quality. `--min-score 0` turns off the score check, so the loop stops only when there are no blocking issues left. The blocking check is never off. A score is not a pass while a critic still names something blocking.

Reject invalid values with the valid range and ask again. Do not round or clamp them. Warn once if M is above 5, because each round costs one builder and every critic, and a gap that survives five rounds is rarely closed by a sixth. Ask only if the goal is missing. Everything else has a default.

Echo the resolved config in one line before going on: goal, floor, cap, critics.

## 2. Context

Read the project before anyone builds. Look at existing code, components, tokens and theme files, design files, docs, READMEs, and any `design-system.md` or `CLAUDE.md` conventions. Then write `context.md` in the session scratchpad. It is run state, not a deliverable, so never write it into the project tree.

Write conventions as checkable lines with the file they came from. An adjective resolves to nothing, so a critic handed one just agrees with itself. A line with a value and a path resolves to yes or no:

- not "consistent styling", but "colours come from `src/theme/tokens.ts`; no raw hex in components"
- not "matches the existing UI", but "buttons are `<Button variant>` from `src/ui/Button.tsx`, never a bare `<button>`"
- not "same tone as the docs", but "docs use second person and imperative headings (`docs/guide.md`)"

State every exception exactly. "No px except 1px borders" leaves open whether a 1px `box-shadow` ring counts, and a strict critic then decides differently each round. Write "only `border` may use 1px" instead. Only write what the project actually does. A convention you inferred from one file is a guess, so say so on that line or leave it out. Scope follows the goal: list the conventions that the thing being built will touch, not the whole codebase.

**Empty project:** if there is nothing to be consistent with, skip `context.md`, drop the consistency critic, and say the build is greenfield from the request. Do not invent conventions to fill the gap. A consistency critic grading against made-up rules is grading noise.

Show `context.md` in one short block and continue. Do not wait for approval unless the user asked to review it.

## 3. Preflight

A check, not a question. Report it in one block:

- Confirm you can render the output: screenshots for UI, a filmstrip for motion, a PDF render for a document, the actual run output for a CLI or API. Capture a component at its own bounds, not inside a full-page shot. Without a render the craft critic goes blind.
- Record the starting commit (`git rev-parse HEAD`) as the diff base for the consistency critic, and note whether the tree was already dirty. With no git repo, or a repo with no commits yet (`rev-parse` fails), pass an empty base, and the critic reads the files the builder lists instead.
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

| Critic | Blocking means | Verdict | Sees | Model | Why |
| --- | --- | --- | --- | --- | --- |
| **Brief** | A stated requirement is not met. Anything the request did not ask for is never blocking. | pass/fail | rendered output | `sonnet` | Simple judgment |
| **Consistency** | A line of `context.md` is clearly broken. Any listed line, however small, is always blocking. Anything not listed is never blocking. If the critic has to interpret a line to decide, it is a gap. | pass/fail | rendered output **and the diff** | `sonnet` | Reusing a component, token, or pattern is a property of the code, so this is the one critic allowed to read it |
| **Craft** | A defect a user would actually hit on realistic use for this goal, shown with evidence. Contrived edge cases, taste, and polish are gaps, not blocking. | scored | rendered output only, never code | `opus` | **Never downgrade.** A cheap craft critic passes everything and the loop ends on round one. |

The blocking rule is what makes the loop converge. With one shared rule ("anything an expert would reject"), a fresh craft critic found new blockers in every round of every test run, and the loop never passed on work that was objectively fine.

Any other name in `--critics` (for example `a11y`, `perf`, `copy`) becomes an extra critic. Write a brief and a blocking rule for that lens, and decide whether it is a yes/no check (a11y against WCAG: pass/fail) or a quality judgment (copy: scored). Run it on `sonnet`, rendered output only, unless the lens is inherently about code. Pass `model` explicitly on every critic. Inheriting the parent model either overpays for simple checks or, under a cheap parent, blinds the craft critic. If these model names are gone, map them by the Why column.

### Scores without drift

Scores drift upward when a critic grades against its own last score. These are the countermeasures, and the script enforces all of them:

- Critics never see earlier rounds: no prior scores, no feedback, no builder summary. They get the files changed, how to render them, and the settled decisions (see below). Each round is judged cold.
- Only judgment critics are scored. A yes/no job on a 10-point scale plateaus: a brief critic that had confirmed every requirement still sat at 8 for three rounds.
- One anchored rubric for every scored critic, based on what can be observed, and scored accurately, not harshly:
  - 10: you would hold it up as the example of how to do this
  - 9: excellent, only nits you would mention in passing
  - 8: good, ships as is
  - 7: solid, but one clear gap you would fix before shipping
  - 6: works, but you would send it back
  - 4: major problems
  - 2: misses the goal or is broken

  The anchors used to be written against "a demanding expert". Such an expert can always name a change, so craft never scored above 7 in testing. If craft still never clears 7 on good work, its score carries no signal, so make it pass/fail.

  The default floor is 8 because the rubric defines 8 as "ships as is". A floor of 7 accepts work that the critic itself says has a gap to fix before shipping.
- Blocking issues are listed separately from the score, and any blocking issue fails the critic whatever its score.
- Critics apply their blocking rule strictly. Praise is not useful.

### Feedback to the builder

The builder gets every blocking issue from every failing critic, ranked brief first, then consistency, then the rest, with craft last. If it does not do the job, nothing else matters yet. Each scored critic still under the floor also adds its biggest gap, marked optional: the builder takes a gap only if it stays inside the goal, and never adds features, flags, or options nobody asked for. A critic that passed adds nothing.

Critics forget between rounds, so the builder carries the memory. It gets every round's feedback and its own previous summary. It may **decline** an item that reverses a change an earlier round asked for, or that goes beyond the goal, giving a reason. Each decline goes to later critics as a settled decision. A critic may still block on it, but only by showing a defect the reason does not cover. Without this, the builder flip-flops: one round's critic asks for something, and the next round's critic blocks it. The summary and the feedback history go to the builder only, never to a critic.

A critic that errored or returned nothing is not a pass. It blocks the round until it reports.

`--max-rounds` is a budget ceiling, not a target. The exit is passing. Running out of rounds is reported as unresolved, never as a quiet pass.

## 5. Handback

On a pass, report the round it passed on, each critic's final verdict or score, the files changed, and anything the builder declined, with its reason. The user may disagree with a decline.

On hitting the cap, report:

- each failing critic, its last score, and its last blocking issues in its own words
- the score history per critic, so a plateau is visible
- `recurring`: blocking issues that came back in near-identical words every round
- `churning`: critics that blocked every round, each time on something new
- `lastRoundNew`: blockers first raised in the final round. The builder never saw them, so present them for the user to decide. They are not proof the work failed.
- everything the builder declined, with its reasons
- what you would try next, in one line

**Churn** means the critic's blocking rule is too loose. It keeps finding the next-worst thing and calling it blocking. Tighten that critic's rule or brief, or accept the result. The work is not the problem.

**A recurring issue** usually does not mean the work is hard. It means the builder cannot close it from where it stands. Check these causes in order:

- **`context.md` is wrong, ambiguous, or contradicts itself.** The consistency critic is enforcing a convention the project does not actually follow, one it reads differently each round, or two that conflict. Fix `context.md`.
- **The fix is outside the builder's medium.** It needs an asset or a tool it was not given. Change the builder's inputs.
- **The floor is above what the critic will give.** The critic lists no blocking issues but stays at 7 every round against a floor of 8. Say so; the user may lower the floor or accept the result.

Say which one you think it is. Raising the round cap is almost never the fix.

## What breaks this

- A thin `context.md`, full of adjectives instead of lines a critic can check, so the consistency critic agrees with itself.
- Inventing conventions for an empty project.
- The builder judging its own work. Critics need fresh context.
- Showing critics their earlier scores. Drift follows.
- A loose blocking rule. The critic churns, and the loop never passes.
- A builder that cannot decline. It obeys contradictory rounds and flip-flops, or turns every gap into an unrequested feature.
- Letting a high score override a blocking issue.
- Treating the round cap as a target, or quietly passing work that ran out of rounds.
