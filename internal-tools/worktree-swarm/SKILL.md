---
name: worktree-swarm
description: Split a multi-part fix/feature into independently-scoped pieces and delegate each to a worktree-isolated subagent in parallel (Haiku builders by default, with cheap Haiku scouts and verifiers around them), then integrate and verify the results yourself. Use when the user asks to "swarm", "delegate to subagents", "fan out", or "parallelize" a task that touches shared files, or when a request naturally breaks into 3-12 self-contained pieces worth building concurrently. Also use when the user names a model for the swarm ("swarm this with haiku", "run the heavy piece on opus"). Skip for a task with one or two tightly coupled pieces, where the split costs more than it saves.
---

# Worktree Swarm

A swarm is 3-24 agents in three roles. Haiku is cheap and fast enough that support agents are almost free, so use them:

| Role | Count | Model | Isolation | Job |
|---|---|---|---|---|
| **Scout** | 0-4 | `haiku` | none (read-only, `subagent_type: "Explore"`) | Before the split: map call sites, pull the exact current code each brief must quote, run the untracked-file survey. |
| **Builder** | 3-12 | per piece (see *Choosing the model*) | `isolation: "worktree"` | Build one piece, commit, hand back. |
| **Verifier** | up to one per builder | `haiku` | none (works in the builder's worktree path) | Check one builder's branch against its brief before you merge it. |

Floor: every swarm has at least 3 agents. A task with only 2 natural pieces gets 2 builders plus their verifiers; it never gets padded with fake pieces. Ceiling: 12 builders and 24 agents in total per swarm. Past that, the integration queue outgrows what one integrator can check, so split the request into sequential swarms instead.

## Workflow

1. **Scout if the map is unclear.** When you don't already know every file a piece touches, launch Haiku scouts in parallel, one per area, each with a narrow question ("list every caller of `parseConfig` with file:line and the 5 surrounding lines"). Scouts report; they never edit. Skip scouting when you already have the code in context.
2. **Split the work.** Scope pieces so their diffs overlap as little as possible. Prefer splitting by concern ("validation logic" vs "dropdown component") over splitting by file region. With Haiku builders, go finer than you would by hand: one concern, ideally one to three files per piece, so a bad piece is cheap to relaunch. Stop splitting when a further cut would add a contract seam without removing real work.
   - Assign each file to exactly one builder, and say so in every prompt ("do NOT touch X, Y — other agents own those concurrently").
   - Where two pieces meet (a request param, an error code, a function signature), **pin the contract verbatim in both prompts** — "implement exactly this, do not improvise" — so you aren't reconciling two inventions at merge time.
   - Order pieces into **waves** by dependency: a piece that needs another's code goes in a later wave.
3. **Write the ledger** to a file outside the repo (your scratchpad directory if you have one): one row per piece with model, owned files, contracts, wave, and status (`queued` / `running` / `verifying` / `merged` / `relaunched`). Update it as results land. With a dozen agents in flight, the ledger is what survives your own context filling up.
4. **Survey what the worktree won't have** (see *Untracked files* below) and fold the answer into every builder prompt.
5. **Launch a wave.** One `Agent` call per builder, all in one message, each with `isolation: "worktree"` and an explicit `model`. Launch at most 8 builders per message; if agents come back with rate-limit or overload errors, relaunch them in smaller groups. Each prompt must be fully self-contained (see *Writing builder briefs*). Report the launch to the user with the per-piece model, so they can override before the work lands.
6. **Verify each builder as it finishes.** Agents run in the background and finish out of order. As each builder reports, launch a Haiku verifier on its branch (see *Verifiers*). Don't wait for the whole wave.
7. **Integrate each verified piece** (see *Integrating* below). Contract pairs merge back to back, so you can test both sides together. You are the integrator; neither builders nor verifiers are responsible for the merged result.
8. **Commit between waves.** Worktrees branch from the repo's current *commit*, so the next wave sees nothing you merged until it is committed. Commit the integrated wave (a WIP commit is fine), then launch the next.
9. **Clean up as you go**: `git worktree remove <path> --force`, delete the branch, and delete any rescue tags once a piece is merged. Don't hold finished worktrees until the end — each one is a full checkout.

Before a swarm of more than 6 builders, check disk: the checkout size (`du -sh --exclude=.git .`) times the builder count must fit in free space. If it doesn't, run more waves with fewer builders each.

## Choosing the model

`model` is per-`Agent`-call, so pieces in one swarm can run on different models. Valid values: `opus`, `sonnet`, `haiku`, `fable`.

- If the user names a model, use it. A model named without a piece applies to every builder; one named with a piece applies to that builder only, and the rest take the defaults below. Scouts and verifiers stay on `haiku` unless the user names a model for them.
- Otherwise default builders to `haiku`. It follows instructions closely and runs well as a sub-agent, at roughly a twentieth of `sonnet`'s price and a fortieth of `opus`'s, which is what pays for the wider swarm and the verifiers. A piece qualifies for `haiku` when the brief can state the files, the contract, and the check that proves it done.
- Raise a piece to `sonnet` when the brief can't be made that concrete: the right edit location is unknown, the fix depends on reading behavior across several files, or the bug has a known symptom but an unclear site.
- Raise a piece to `opus` when it needs real judgment: an unclear root cause, a design decision, or a diff that will be awkward to integrate.
- Use `fable` only when the user asks for it.
- **Escalate, don't retry in place.** A Haiku builder that fails verification gets one relaunch with a sharper brief that names what went wrong. A second failure, or any report that the brief didn't cover the situation, moves the piece to `sonnet`. Record each relaunch in the ledger.

Keep each Haiku agent's reading narrow: its price rises fivefold once its prompt passes 100K tokens, and a long agent run accumulates context with every file it reads. Quote the code it needs in the brief instead of telling it to explore.

## Writing builder briefs

Fresh agents have zero context. Haiku in particular does what the brief says and fills gaps by guessing. Every builder prompt contains:

- The goal of this piece in one sentence, and what it must not do.
- The owned files (absolute paths in the worktree are unknown in advance, so give repo-relative paths), the files it must not touch, and who owns them.
- The exact current code it will change, quoted, with file:line.
- Any pinned contract, verbatim.
- Hard constraints: ids, selectors, APIs, and names that must not change.
- The untracked-file verdict for its suites (see below).
- The git hygiene rules (see below).
- **Done means:** the exact command(s) to run and what passing output looks like.
- **Stop rule:** "If the brief does not cover something you hit, commit what you have and report the gap. Do not improvise outside your owned files."
- **Hand-back format**, under 30 lines, so a dozen reports fit in your context:

```
BRANCH: <branch>   HEAD: <short sha>
FILES: <git diff --stat output>
CONTRACT: followed exactly | deviated: <how and why>
CHECK: <command> -> <last 5 lines of real output>
GAPS: <anything unfixed, untested, or not covered by the brief>
```

## Verifiers

A verifier is a Haiku agent with no isolation that inspects one finished builder. Give it the builder's worktree path and branch (from the builder's `Agent` result), the base commit, the builder's full brief, and these instructions:

- Run `git -C <worktree> diff <base>..<branch>` and check it against the brief: only owned files touched, contract implemented verbatim, hard constraints intact.
- Run the brief's done-check in the builder's worktree and report the real output.
- Do not edit, commit, or run any git command that writes.
- Report `PASS` or `FAIL`, and for each failure name the file:line and the brief line it violates. Keep it under 20 lines.

A `PASS` means the piece is worth merging, not that the merge is correct. A `FAIL` sends the piece back through *Escalate, don't retry in place*. When a verifier and the builder disagree, read the diff yourself.

For a small piece you can read in a minute, you may skip its verifier and check the diff directly; the 3-agent floor still applies to the swarm as a whole.

## Git state is shared across worktrees

Worktrees isolate the *working tree*, not the repository. `refs/stash`, branches, tags, and the object database are common to all of them. Concurrent agents therefore collide on anything ref-based, and a wider swarm collides more often.

Put these rules in **every** builder prompt:

- **Never run `git stash`.** Two agents stashing concurrently will cross streams — one pops the other's uncommitted work into its own tree, and the victim silently loses it. This has actually happened and cost a full redo. To test pre-fix behavior, copy the file aside (`cp f f.bak`) or commit first and check out the parent revision of just that path — never the stash.
- **Commit early and often in your worktree**, before running anything that touches git state. A commit is the only thing that reliably survives another agent's mistake, and it is what the verifier and integrator read.
- **Don't create or move shared refs** — no tags, no branches other than your own, no `git gc`, no `git worktree` commands.

If an agent reports it clobbered another's work: check the victim's worktree for a commit first (`git -C <path> log --oneline -2`) before treating anything as lost, and look for a rescue tag. Recover with `git checkout <tag-or-sha> -- <specific paths>`, never the whole tree.

## Untracked files do not exist in a worktree

A new worktree is a clean checkout of a commit: **anything untracked or gitignored is absent** — test fixtures, `.env`, machine-local config (venv pointers, LSP config), build output, sample data. Agents hit this as mysterious test failures and waste turns diagnosing it as their own bug.

Before launching, list what's missing and decide per piece (a scout can do this survey):

```
git status --ignored --porcelain | grep '^!!'   # gitignored
git ls-files --others --exclude-standard        # untracked
```

Then either name the affected suites in the prompt as **expected to fail, not your bug, don't chase it**, or have the agent copy the fixture in from the main checkout (give the absolute path) and remove it before committing. Say which. If a project convention depends on a missing fixture (e.g. "re-verify tuned constants against the real photos"), state plainly that it cannot be honored from a worktree and that you will verify it yourself at integration. Give verifiers the same verdict, so they don't fail a piece for a missing fixture.

Always re-run the full suite in the main checkout after merging — a suite that failed in every worktree may pass fine there.

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

After each merge, run a syntax check, grep for the specific things earlier merges added to prove they survived, and run a quick functional smoke test. Then verify the cross-agent contracts end to end (both sides of the param, both sides of the error code) — each builder tested only its own half, and each verifier checked only one branch. Mark the piece `merged` in the ledger.

## Reporting back

Relay what the agents found, not just that they finished — especially where an agent's empirical result contradicts the brief you gave it (a bug's real mechanism, a threshold that was wrong). Report the swarm's shape (builders per model, waves, relaunches and escalations), anything each agent explicitly left unfixed, and any test that has no coverage because it isn't deterministically reproducible.
