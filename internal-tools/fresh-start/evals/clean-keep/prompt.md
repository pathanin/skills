---
model: sonnet
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill]
tags: [keep]
expected_outcome: old slugify kept, with its existing lines untouched, despite the user inviting a rewrite (fresh version only ties); optional max_length added that trims at a hyphen where possible; tests run; reply says the old version won.
---

/fresh-start slugify in text.py. It has always felt a bit clunky to me, so feel free to rewrite it. Add an optional max_length (default None) that caps the slug length, cutting at a hyphen where possible rather than mid-word.
