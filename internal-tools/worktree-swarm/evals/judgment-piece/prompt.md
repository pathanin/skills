---
model: opus
max_turns: 150
timeout_seconds: 2400
allowed_tools: [Read, Glob, Grep, Edit, Write, Bash, Agent, Skill]
tags: [below-floor, model-choice]
expected_outcome: Below the swarm floor (4 pieces): no Haiku worktree swarm. All 8 tests pass, protected files untouched, no worktree or agent branch left, and the reply relays the real root cause (int() truncating float * 100).
---

Swarm this. The ledger CLI is missing three modules (see SPEC.md). Also, users say some monthly totals come out a cent low, and nobody knows why; find the cause and fix it. Don't touch cli.py, the tests, or the sample data.

When everything is merged and cleaned up, finish by running `./check.sh > check-output.txt` in the repo root.
