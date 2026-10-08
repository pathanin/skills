---
model: opus
max_turns: 150
timeout_seconds: 2700
allowed_tools: [Read, Glob, Grep, Edit, Write, Bash, Agent, Skill]
tags: [fire, ceiling]
expected_outcome: Six unit modules built by six worktree builders on haiku (registry.py pinned as the shared contract in every brief), each finished builder checked by an opus verifier at low effort, all 20 tests pass, registry.py and the tests untouched, every worktree and agent branch removed, and the reply reports the per-piece model choice.
---

Swarm this. unitconv needs its six unit modules (length, mass, temperature, volume, speed, data). docs/units.md has the spec and the tests are already in tests/. registry.py is a shared contract, so don't change it.

When everything is merged and cleaned up, finish by running `./check.sh > check-output.txt` in the repo root.
