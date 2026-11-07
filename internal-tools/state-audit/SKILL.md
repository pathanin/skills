---
name: state-audit
description: Manual-only state machine audit, invoked with /state-audit. Maps the app's explicit and implicit state machines into one document (states, invariants, transition tables), finds invalid states and transitions the code can actually reach, including through retries and concurrency, then fixes the confirmed bugs with regression tests and keeps the document current.
argument-hint: "[path or area to audit; default: whole app]"
disable-model-invocation: true
---

# State Audit

Scope: $ARGUMENTS (empty means the whole app).

Find the app's state machines, both the explicit ones and the implicit ones nobody wrote down,
and document their states, invariants and transition tables in one file. Use the repo's
existing doc if there is one, otherwise `docs/state-machines.md`.

Then find the invalid states or transitions the code can actually reach, including through
retries and concurrency. Back each one with evidence: a failing test, a repro, or a trace
through the real code. Keep anything you can't confirm separate as suspected, and don't fix it.

Prioritize confirmed bugs by impact and group related fixes into issues in the document.
Fix them with regression tests that fail before the fix, and keep the document updated as
you go. Ask me before fixes that are really product decisions, such as data migrations or
changes to a public API.
