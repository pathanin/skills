---
model: opus
max_turns: 100
timeout_seconds: 1800
allowed_tools: [Read, Glob, Grep, Edit, Write, Bash, Agent, Skill]
tags: [fire, floor]
expected_outcome: Two worktree builders on haiku (server validation, client message) with the error code pinned verbatim in both briefs, at least one opus verifier at low effort so the swarm reaches the 3-agent floor, no padded third builder, all tests pass, worktrees and agent branches removed.
---

Swarm this: signup needs username validation. On the server, server/validate.py must reject a username unless it is 3-20 characters of lowercase a-z, digits or underscore (a missing username is invalid too). On the client, client/messages.py must show "Usernames use 3-20 lowercase letters, digits or underscores." for that error. Pick the error code yourself. tests/test_username.py is the acceptance test.

When everything is merged and cleaned up, finish by running `./check.sh > check-output.txt` in the repo root.
