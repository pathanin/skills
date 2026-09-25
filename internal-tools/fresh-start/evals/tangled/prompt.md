---
model: sonnet
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill]
tags: [rewrite]
expected_outcome: shipping_cost rewritten simply; free shipping over 100 added; BT/JE/GY/IM +4.00 surcharge still charged on free orders, because the commit message says it is a carrier pass-through; order["shipping_zone"] still set for invoice.py; EU express +8.00 bug surfaced to the user; tests run; no leftover second implementation.
---

/fresh-start shipping_cost in pricing.py. I need to add free shipping: when order["subtotal"] is over 100, shipping is free, except express still costs the usual 8.00. Every time I touch this function something else breaks.
