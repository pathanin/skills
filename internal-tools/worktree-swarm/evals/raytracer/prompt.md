---
model: opus
max_turns: 250
timeout_seconds: 3600
allowed_tools: [Read, Glob, Grep, Edit, Write, Bash, Agent, Skill]
tags: [fire, large, visual]
expected_outcome: All thirteen SPEC.md modules built and merged, all 63 tests pass, render.py produces out/final.png and out/views.png, protected files untouched, worktrees and agent branches removed. Scored on outcomes; time, cost and swarm shape are reported, not scored.
---

Swarm this. tinyrt is a ray tracer that's missing the thirteen modules described in SPEC.md: shapes, meshes, an OBJ loader, a BVH, the camera, textures, lighting, the tracer, the scene loader and tone mapping. The tests are in tests/, and rt/types.py is the shared contract, so don't change it. I'll judge the result by the images render.py writes into out/.

When everything is merged and cleaned up, finish by running `./check.sh > check-output.txt` in the repo root.
