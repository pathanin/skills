---
name: worktree-swarm
description: Run a genuinely large build as a swarm of 8-24 worktree-isolated builders (Haiku by default), then integrate and verify the results yourself. Use only when the work splits into 8 or more substantial, independent pieces, each its own files and real implementation work (roughly 100+ lines or a non-trivial multi-file change), and the user asks to "swarm", "fan out" or "parallelize" it or the request plainly has that shape. Also use when the user names models for such a swarm ("swarm this with haiku", "run the renderer on opus"). Skip anything smaller, even when the user says "swarm" or "parallelize": with fewer than 8 substantial pieces, plain parallel Agent calls on the session model (or doing it yourself) finish sooner at the same or lower cost.
---

# Worktree Swarm

A swarm is for builds big enough that the building itself dominates the cost. Haiku builders cost a fortieth of Opus per token, which pays off when there are many pieces of real implementation work. On smaller jobs the swarm's fixed overhead (briefs, base checks, verification, integration) costs more than it saves: measured on 2-7 piece tasks, it produced the same code as plain Opus subagents, 60% slower and 10-15% more expensive.

## Size gate

Count the pieces before anything else. A piece is substantial when it is its own set of files with real implementation work: roughly 100+ lines of new code, or a non-trivial change across several files. A one-function edit, a constant, or a wiring change is not a piece; fold it into a neighbour or do it yourself.

- **8-24 substantial pieces:** run the swarm below.
- **Fewer than 8:** don't use this skill. Tell the user in one line that the task is below the swarm floor, then do it with plain parallel `Agent` calls (worktree isolation where pieces share files, no model override) or by yourself.
- **More than 24:** split the request into sequential swarms of at most 24 builders, each integrated and committed before the next starts. Past 24, one integrator can't keep up with the merge queue.

| Role | Count | Model | Isolation | Job |
|---|---|---|---|---|
| **Scout** | 0-4 | `haiku` | none (read-only, `subagent_type: "Explore"`) | Before the split: map call sites, pull the exact code briefs must quote, run the untracked-file survey. |
| **Builder** | 8-24 | per piece (see *Choosing the model*) | `isolation: "worktree"` | Build one piece, commit, reply. |
| **Verifier** | only where needed (see *Verifiers*) | `opus`, `effort: "low"` | none (works in the builder's worktree path) | Check one branch against the spec where the tests can't. |

## Workflow

1. **Scout if the map is unclear.** When you don't already know every file a piece touches, launch Haiku scouts in parallel, one per area, each with a narrow question ("list every caller of `parseConfig` with file:line and the 5 surrounding lines"). Scouts report; they never edit. Skip scouting when you already have the code in context.
2. **Split the work.** Scope pieces so their diffs overlap as little as possible, by concern rather than by file region.
   - Assign each file to exactly one builder, and say so in every brief.
   - Where two pieces meet (a function signature, a data shape, an error code), **pin the contract verbatim in both briefs** — "implement exactly this, do not improvise" — so you aren't reconciling two inventions at merge time.
   - Order pieces into **waves** by dependency: a piece that needs another's code goes in a later wave.
3. **Write the ledger** to a file outside the repo (your scratchpad directory if you have one): one row per piece with model, owned files, contracts, wave, and status (`queued` / `running` / `merged` / `relaunched`). Update it as results land. With 8-24 agents in flight, the ledger is what survives your own context filling up.
4. **Survey what the worktree won't have** (see *Untracked files* below) and fold the answer into the briefs it affects.
5. **Launch builders.** One `Agent` call per builder, each with `isolation: "worktree"` and an explicit `model`, at most 8 per message. Agents run in the background, so launch the next group as earlier ones finish. If agents come back with rate-limit or overload errors, relaunch them in smaller groups. If the call is refused because worktree isolation is unavailable, never relaunch the builders into the shared checkout: create one worktree per builder yourself (`git worktree add -b swarm/<piece> <abs-path>` from your `HEAD`), launch each builder without `isolation`, and make the first line of its brief "Work only inside `<abs-path>`; `cd` there before every command and use absolute paths under it for every file edit." Integrate and clean up those branches the same way. Report the launch to the user with the per-piece model, so they can override before the work lands.
6. **Integrate each piece as it finishes** (see *Integrating* below), then run the full test suite in the main checkout. The suite is the default check. Add a verifier only where *Verifiers* says so. You are the integrator; builders are not responsible for the merged result.
7. **Commit between waves.** Worktrees branch from the repo's current *commit*, so the next wave sees nothing you merged until it is committed. Commit the integrated wave (a WIP commit is fine), then launch the next.
8. **Clean up as you go**: `git worktree remove <path> --force`, delete the branch, and delete any rescue tags once a piece is merged. Don't hold finished worktrees until the end — each one is a full checkout.

Before launching, check disk: the checkout size (`du -sh --exclude=.git .`) times the number of builders running at once must fit in free space. If it doesn't, launch smaller groups.

## Choosing the model

`model` is per-`Agent`-call, so pieces in one swarm can run on different models. Valid values: `opus`, `sonnet`, `haiku`, `fable`.

- If the user names a model, use it. A model named without a piece applies to every builder; one named with a piece applies to that builder only, and the rest take the defaults below. Scouts stay on `haiku` and verifiers on `opus` with `effort: "low"` unless the user names a model for them.
- Otherwise default builders to `haiku`, at roughly a twentieth of `sonnet`'s price and a fortieth of `opus`'s. A piece qualifies for `haiku` when the brief can state the files, the contract, and the check that proves it done.
- Raise a piece to `sonnet` when the brief can't be made that concrete: the right edit location is unknown, the fix depends on reading behavior across several files, or the bug has a known symptom but an unclear site.
- Raise a piece to `opus` when it needs real judgment: an unclear root cause, a design decision, or a diff that will be awkward to integrate.
- Use `fable` only when the user asks for it.
- **Escalate, don't retry in place.** A Haiku piece that fails its done-check at integration, or fails verification, gets one relaunch with a sharper brief that names what went wrong. A second failure, or any report that the brief didn't cover the situation, moves the piece to `sonnet`. Record each relaunch in the ledger.

Keep each Haiku agent's reading narrow: its price rises fivefold once its prompt passes 100K tokens, and a long agent run accumulates context with every file it reads. Point it at the spec section and quote the code it changes instead of telling it to explore.

## Writing builder briefs

Fresh agents have zero context and Haiku fills gaps by guessing, but long briefs cost integrator tokens on every piece. Keep each brief to what the builder can't infer:

- The goal in one sentence, and the spec section or the exact current code (quoted, with file:line) it works from.
- The files it owns, and the files it must not touch because other agents own them.
- Any pinned contract, verbatim.
- **Done means:** the exact command that proves the piece works.
- One line of git rules: "Never run `git stash`. Commit in your worktree before running anything that touches git. Create no tags or other branches."
- One line of stop rule: "If the brief doesn't cover something, commit what you have and say what's missing; don't edit outside your files."
- One line of reply format: "Reply with your branch, commit sha, and the last lines of the done-check output."

Add the untracked-file verdict (see below) only to briefs whose tests it affects.

## Verifiers

Integration runs the full suite, so a verifier that only re-runs a builder's tests adds cost and catches nothing. Launch one for a piece only when:

- the spec has rules no test exercises (formulas, clamps, ordering, exact output text), or
- the piece is one side of a contract whose other side isn't merged yet, or
- the builder's done-check output looks wrong or its reply admits a gap.

A verifier is an `Agent` call with `model: "opus"`, `effort: "low"`, no isolation, and exactly one branch. Give it the builder's worktree path and branch, the base commit, the spec rules it must check, and these instructions:

- Run `git -C <worktree> diff <base>..<branch>`. Check it line by line against the listed spec rules and the pinned contract, not just the tests. Name each rule you checked.
- Confirm only the piece's own files changed.
- Do not edit, commit, or run any git command that writes.
- Report `PASS` or `FAIL`, naming file:line and the violated rule for each failure, in under 15 lines.

A `FAIL` sends the piece back through *Escalate, don't retry in place*. When a verifier and the builder disagree, read the diff yourself.

## Git state is shared across worktrees

Worktrees isolate the *working tree*, not the repository. `refs/stash`, branches, tags, and the object database are common to all of them, so concurrent agents collide on anything ref-based, and a wider swarm collides more often. That's why every brief carries the one-line git rule. `git stash` is the dangerous one: two agents stashing concurrently cross streams, one pops the other's uncommitted work into its own tree, and the victim silently loses it. This has happened and cost a full redo.

If an agent reports it clobbered another's work: check the victim's worktree for a commit first (`git -C <path> log --oneline -2`) before treating anything as lost, and look for a rescue tag. Recover with `git checkout <tag-or-sha> -- <specific paths>`, never the whole tree.

## Untracked files do not exist in a worktree

A new worktree is a clean checkout of a commit: **anything untracked or gitignored is absent** — test fixtures, `.env`, machine-local config, build output, sample data. Agents hit this as mysterious test failures and waste turns diagnosing it as their own bug.

Before launching, list what's missing (a scout can do this survey):

```
git status --ignored --porcelain | grep '^!!'   # gitignored
git ls-files --others --exclude-standard        # untracked
```

For each affected piece, either name the affected suites in its brief as **expected to fail, not your bug, don't chase it**, or have the agent copy the fixture in from the main checkout (give the absolute path) and remove it before committing. If a project convention depends on a missing fixture, say it can't be honored from a worktree and verify it yourself at integration.

## Integrating

**Check the base before touching a diff.** Worktrees branch from the repo's current commit at *launch* time, which may be behind your `HEAD` — and your own uncommitted edits are never in it:

```
git merge-base HEAD worktree-agent-<id>
```

If that isn't your `HEAD`, a wholesale merge will revert whatever landed in between. In a swarm this is the normal case after the first merge. Port per file instead:

- Files untouched by the intervening commits: `git checkout <branch> -- <paths>` takes them verbatim.
- Files that did change: three-way apply the agent's delta from its own base, which merges rather than reverts —
  `git diff <base> <branch> -- <paths> | git apply -3`
- Genuine conflict, or a diff you don't trust: port the *logic* by hand onto your actual working file.

After each merge, run the full suite and check that earlier merges survived. Then verify the cross-agent contracts end to end (both sides of the signature, both sides of the data shape) — each builder tested only its own half. Mark the piece `merged` in the ledger.

## Reporting back

Relay what the agents found, not just that they finished, especially where a result contradicts the brief you gave (a bug's real mechanism, a threshold that was wrong). Report the swarm's shape (builders per model, waves, verifiers launched and why, relaunches and escalations), anything an agent left unfixed, and any behavior no test covers.
