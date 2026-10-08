---
model: opus
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Read, Glob, Grep, Edit, Write, Bash, Agent, Skill]
tags: [below-floor, visual]
expected_outcome: Below the swarm floor (7 modest modules): no Haiku worktree swarm. All 29 tests pass, make_movie renders out/sheet.png and out/final.png with physics in bounds, protected files untouched, no worktree or agent branch left.
---

Swarm this. ballpit is a small 3D ball-physics simulation with a ray-traced renderer, and it's missing the seven modules described in SPEC.md. The tests are in tests/, and world.py is the shared contract, so don't change it. I'll judge the result by the images make_movie.py renders into out/.

When everything is merged and cleaned up, finish by running `./check.sh > check-output.txt` in the repo root.
