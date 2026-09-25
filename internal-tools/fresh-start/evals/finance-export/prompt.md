---
model: sonnet
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill]
tags: [rewrite, sprawl]
expected_outcome: export_orders cleaned up; test orders (email ending @example.com, any case) skipped and not counted; a sixth column country_code added exactly as finance's importer and docs/finance-export.md specify (capitals, ZZ when unknown), found without being told where; otherwise the bytes finance imports unchanged (LF, no quoting, commas in names become spaces); still writes to a .tmp file and renames it; customer/email/currency/country None handled; tests run and updated for the new column; reply ties the format to finance's importer. Expects the agent to finish, not ask.
---

/fresh-start export_orders in shopkit/export.py. This file is a mess, clean it up. Also, test orders must stop showing up in the export: skip any order whose email ends in @example.com, in any letter case. And finance asked for each order's country in the export.
