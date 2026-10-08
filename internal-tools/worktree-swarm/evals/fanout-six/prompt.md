---
model: opus
max_turns: 150
timeout_seconds: 2700
allowed_tools: [Read, Glob, Grep, Edit, Write, Bash, Agent, Skill]
tags: [below-floor, ceiling]
expected_outcome: Below the swarm floor (6 small pieces): the skill stays out, no Haiku worktree swarm runs, and the work is done with plain subagents or solo. All 20 tests pass, registry.py and the tests untouched, no worktree or agent branch left.
---

Swarm this. unitconv needs its six unit modules (length, mass, temperature, volume, speed, data). docs/units.md has the spec and the tests are already in tests/. registry.py is a shared contract, so don't change it.

When everything is merged and cleaned up, finish by running `./check.sh > check-output.txt` in the repo root.
