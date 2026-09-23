---
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill]
tags: [build]
expected_outcome: one self-contained stats.html; numeric sort; even-count median averages the middle pair; blank lines never become zeros; plain styling.
---

/build-fast Make me stats.html: I paste numbers into it, one per line, and it shows the count, sum, mean and median.
