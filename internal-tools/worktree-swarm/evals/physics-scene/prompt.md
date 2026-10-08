---
model: opus
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Read, Glob, Grep, Edit, Write, Bash, Agent, Skill]
tags: [fire, visual]
expected_outcome: The seven SPEC.md modules (integrate, walls, collide, camera, raster, scene, sheet) built by haiku worktree builders with complete briefs, world.py pinned as the contract, one opus low-effort verifier per branch; all 28 tests pass; make_movie renders out/sheet.png and out/final.png with physics metrics in bounds; protected files untouched; worktrees and agent branches removed.
---

Swarm this. ballpit is a small 3D ball-physics simulation with a ray-traced renderer, and it's missing the seven modules described in SPEC.md. The tests are in tests/, and world.py is the shared contract, so don't change it. I'll judge the result by the images make_movie.py renders into out/.

When everything is merged and cleaned up, finish by running `./check.sh > check-output.txt` in the repo root.
