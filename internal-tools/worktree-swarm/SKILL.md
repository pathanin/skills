---
name: worktree-swarm
description: Split a multi-part fix/feature into independently-scoped pieces and delegate each to a worktree-isolated subagent in parallel, then manually integrate and verify the results yourself. Use when the user asks to "swarm", "delegate to subagents", or "parallelize" a task that touches shared files, or when a request naturally breaks into 2-4 self-contained pieces worth building concurrently.
---

# Worktree Swarm

For a task with 2-4 pieces that could be built concurrently but touch overlapping files:

1. **Split the work** into pieces scoped so their diffs overlap as little as possible. Prefer splitting by concern (e.g. "validation logic" vs "dropdown component") over splitting by file region. Assign each file to exactly one agent and say so in every prompt ("do NOT touch X, Y — other agents own those concurrently"). Where two pieces must meet (a request param, an error code, a function signature), **pin the contract verbatim in both prompts** — "implement exactly this, do not improvise" — so you aren't reconciling two inventions at merge time.
2. **Before launching, survey what the worktree won't have** (see *Untracked files* below) and fold the answer into every prompt.
3. **Launch one `Agent` call per piece, in parallel (one message, multiple tool calls), each with `isolation: "worktree"`.** Fresh agents have zero context — each prompt must be fully self-contained: relevant file paths, exact current code snippets, hard constraints (ids/APIs that must not change), the git hygiene rules below, and what to hand back (a `git diff --stat` + short summary + real test output).
4. **Do not treat the raw diffs as mergeable patches** (see *Integrating* below).
5. **Integrate sequentially, verify after each merge** (syntax check, grep for ids/selectors that must survive, a quick functional smoke test). You are the integrator; the agents are not responsible for the merged result.
6. **Clean up**: `git worktree remove <path> --force`, delete the branch, and delete any rescue tags once a piece is merged.

Keep pieces small enough that a bad one is cheap to redo solo instead of re-merging.

## Git state is shared across worktrees

Worktrees isolate the *working tree*, not the repository. `refs/stash`, branches, tags, and the object database are common to all of them. Concurrent agents therefore collide on anything ref-based.

Put these rules in **every** agent prompt:

- **Never run `git stash`.** Two agents stashing concurrently will cross streams — one pops the other's uncommitted work into its own tree, and the victim silently loses it. This has actually happened and cost a full redo. To test pre-fix behavior, copy the file aside (`cp f f.bak`) or commit first and check out the parent revision of just that path — never the stash.
- **Commit early and often in your worktree**, before running anything that touches git state. A commit is the only thing that reliably survives another agent's mistake, and it is what the integrator reads.
- **Don't create or move shared refs** — no tags, no branches other than your own, no `git gc`.

If an agent reports it clobbered another's work: check the victim's worktree for a commit first (`git -C <path> log --oneline -2`) before treating anything as lost, and look for a rescue tag. Recover with `git checkout <tag-or-sha> -- <specific paths>`, never the whole tree.

## Untracked files do not exist in a worktree

A new worktree is a clean checkout of a commit: **anything untracked or gitignored is absent** — test fixtures, `.env`, machine-local config (venv pointers, LSP config), build output, sample data. Agents hit this as mysterious test failures and waste turns diagnosing it as their own bug.

Before launching, list what's missing and decide per piece:

```
git status --ignored --porcelain | grep '^!!'   # gitignored
git ls-files --others --exclude-standard        # untracked
```

Then either name the affected suites in the prompt as **expected to fail, not your bug, don't chase it**, or have the agent copy the fixture in from the main checkout (give the absolute path) and remove it before committing. Say which. If a project convention depends on a missing fixture (e.g. "re-verify tuned constants against the real photos"), state plainly that it cannot be honored from a worktree and that you will verify it yourself at integration.

Always re-run the full suite in the main checkout after merging — a suite that failed in every worktree may pass fine there.

## Integrating

**Check the base before touching a diff.** Worktrees branch from the repo's current commit at *launch* time, which may be behind your `HEAD` — and your own uncommitted edits are never in it:

```
git merge-base HEAD worktree-agent-<id>
```

If that isn't your `HEAD`, a wholesale merge will revert whatever landed in between. Port per file instead:

- Files untouched by the intervening commits: `git checkout <branch> -- <paths>` takes them verbatim.
- Files that did change: three-way apply the agent's delta from its own base, which merges rather than reverts —
  `git diff <base> <branch> -- <paths> | git apply -3`
- Genuine conflict, or a diff you don't trust: port the *logic* by hand onto your actual working file.

After each merge, grep for the specific things the intervening commits added, to prove they survived. Then verify the cross-agent contracts end to end (both sides of the param, both sides of the error code) — each agent tested only its own half.

## Reporting back

Relay what the agents found, not just that they finished — especially where an agent's empirical result contradicts the brief you gave it (a bug's real mechanism, a threshold that was wrong). Note anything each agent explicitly left unfixed, and any test that has no coverage because it isn't deterministically reproducible.
