---
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill]
tags: [rewrite]
expected_outcome: shipping_cost rewritten simply; BT/JE/GY/IM +4.00 surcharge kept (found in git history); EU express +8.00 bug surfaced to the user; free shipping over 100 added; tests run; no leftover second implementation.
---

/fresh-start shipping_cost in pricing.py. I need to add free shipping: when order["subtotal"] is over 100, waive the base rate including the weight charge, but still charge express and any surcharges. Every time I touch this function something else breaks.
