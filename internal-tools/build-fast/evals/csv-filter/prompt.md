---
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill]
tags: [build]
expected_outcome: big_orders.csv holds A1002 A1004 A1007 A1008 A1010 A1012 A1014; total 6894.34; A1005 and A1009 reported as unparseable.
---

/build-fast orders.csv is in this folder. I need big_orders.py: it writes big_orders.csv with every order over $500 and prints the total of those orders. I'll re-run it on next month's export.
