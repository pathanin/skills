---
model: opus
max_turns: 100
timeout_seconds: 1800
allowed_tools: [Read, Glob, Grep, Edit, Write, Bash, Agent, Skill]
tags: [below-floor, floor]
expected_outcome: Below the swarm floor (2 pieces): no Haiku worktree swarm. All tests pass, protected files untouched, no worktree or agent branch left.
---

Swarm this: signup needs username validation. On the server, server/validate.py must reject a username unless it is 3-20 characters of lowercase a-z, digits or underscore (a missing username is invalid too). On the client, client/messages.py must show "Usernames use 3-20 lowercase letters, digits or underscores." for that error. Pick the error code yourself. tests/test_username.py is the acceptance test.

When everything is merged and cleaned up, finish by running `./check.sh > check-output.txt` in the repo root.
