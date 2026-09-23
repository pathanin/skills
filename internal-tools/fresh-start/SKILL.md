---
name: fresh-start
description: >
  Treat existing code as a spec, not a foundation: pull out the behavior it has to keep,
  write an independent implementation from that behavior, compare the two, and keep
  whichever is simpler and correct. Trigger on "start fresh", "rewrite this from scratch",
  "clean-slate this", "should I just rewrite this", "this code is a mess, can you fix/change
  it", "every fix breaks something else", or when the user is changing a function, module,
  or small codebase they call awkward, brittle, tangled, or hard to modify. Also trigger when
  two patches to the same code have already failed in this conversation, or when the user asks
  to /fresh-start. Works at any size, from one function to a small codebase. Skip when the code
  is clean and the change is local, for one-line or config fixes, for style-only complaints
  ("rename this", "reformat this"), for large codebases where the user asked for an
  incremental migration, and when the user has said to keep the existing structure.
---

# Fresh Start

Existing code is evidence of what the system must do. It is not proof of how to do it.
Your job is to escape anchoring on that code: read it for its behavior, then pick the
simplest correct starting point, whether that is the old code or a clean rewrite.

This is not a license to rewrite. A rewrite has to beat the old code on the comparison in
step 4. If it only ties, keep the old code, because a tie still costs review time, churn,
and risk.

## 1. Pick the unit

Choose the smallest unit whose outside boundary you can hold fixed: one function, one
class, one module, or one script. Callers, the public signature, file formats, and side
effects on the boundary stay as they are unless the user says otherwise. Everything inside
the boundary is open.

If no stable boundary exists below "the whole codebase", say so and ask before going
further. That is a migration, not a fresh start.

## 2. Pull the behavior contract out of the old code

Read the old code, its tests, its callers, and `git log -p` / `git blame` on the
confusing parts. Write a short contract as a plain list:

- **Inputs and outputs**: types, shapes, and ranges actually passed in by real callers.
- **Side effects**: writes, network calls, mutations of arguments, logging that someone
  greps for, ordering that callers rely on.
- **Edge cases**: empty input, missing keys, duplicates, unicode, time zones, very large
  input, and whatever the old code special-cases.
- **Error behavior**: what raises, what returns a default, and what fails silently.
- **Suspected bugs**: behavior that looks wrong. Keep these separate from the contract.

Every odd branch, magic number, or special case is a candidate requirement. Before
dropping one, find out why it exists (commit message, linked issue, test, comment). If you
cannot find out, keep it in the contract and mark it `unexplained`. Never drop behavior
just because you can't see its purpose.

## 3. Write the fresh version from the contract

Close the old code. Write the new version from the contract list alone, as if the old
implementation didn't exist. Don't copy its structure, its helper names, or its control
flow. If you catch yourself reproducing its shape, stop and ask whether the contract
actually needs that shape.

Aim for the most direct code that satisfies the contract: fewer branches, fewer layers,
and no indirection that the contract does not require. Keep the boundary from step 1.

Scale the effort to the unit. For one function, do this inline in a few minutes. For a
module, write the new version alongside the old one (e.g. `foo_new.py`, or a second
function) so that both can run during step 4.

## 4. Compare both versions

Run both versions against the same inputs:

1. The existing test suite, if there is one.
2. Every edge case from the contract.
3. A differential check: feed identical inputs to old and new and diff the outputs. Use
   real inputs where you can get them. For pure functions, add a quick loop over generated
   inputs.

Classify every difference as one of:

- **Old bug**: the new version is right. List it for the user; don't quietly ship the change.
- **New bug**: fix the fresh version, or count it against it.
- **Unexplained**: the contract can't tell you which version is right. Ask the user.

Then compare the two on:

| Criterion | Question |
|---|---|
| Correctness | Which version passes more of the contract, with fewer known bugs? |
| Edge cases | Which one handles the listed cases explicitly rather than by accident? |
| Simplicity | Fewer branches, layers, and special cases for the same behavior? |
| Readability | Could someone new predict what it does from reading it once? |
| Changeability | How big is the diff for the change that prompted this work, in each version? |

## 5. Choose one and remove the other

Choose one of these outcomes:

- **Fresh version**: it is correct on the contract and clearly simpler. Replace the old
  code in place, delete the scaffolding, and keep or port the old tests.
- **Old version**: the fresh version was not clearly better. Keep the old code, apply the
  original change to it, and fold in any old bugs found in step 4 only if the user agrees.
- **Hybrid**: the fresh version's structure with specific pieces of old logic that proved
  correct (usually the `unexplained` cases). Say which pieces came from where.

Never leave both implementations in the codebase, and don't add a flag to switch between
them unless the user asks for one.

Stop and ask before replacing when any of these apply:

- the unit has no tests and no callers you can run, so you can't verify the comparison
- the fresh version changes behavior that external callers or stored data may depend on
- the user asked for a minimal change and the rewrite touches far more lines than that

## 6. Report

Tell the user, in this order:

1. **The choice** (fresh, old, or hybrid) and the one-line reason from the comparison.
2. **Behavior differences**: old bugs fixed, behaviors preserved on purpose, and any
   `unexplained` cases and how you resolved them.
3. **How you verified it**: which tests and differential checks ran, and what they showed.
4. **Size change**, when it is informative (e.g. "140 → 55 lines, 9 → 3 branches").

If the old code won, say so plainly. Finding out the existing code was already the simplest
correct starting point is a valid result of this skill.
