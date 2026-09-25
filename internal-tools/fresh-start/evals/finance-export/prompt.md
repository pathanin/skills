---
model: sonnet
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill]
tags: [rewrite, sprawl]
expected_outcome: export_orders cleaned up; test orders (email ending @example.com, any case) skipped and not counted; output bytes unchanged for finance's importer (LF, no quoting, commas in names become spaces); still writes to a .tmp file and renames it into place; customer/email/currency None handled; tests run; reply names the finance importer as why the format stayed. Expects the agent to finish, not ask.
---

/fresh-start export_orders in shopkit/export.py. This file is a mess, clean it up. Also, test orders must stop showing up in the export: skip any order whose email ends in @example.com, in any letter case.
