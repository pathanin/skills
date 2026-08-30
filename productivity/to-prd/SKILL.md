---
name: to-prd
description: Turn the current conversation context into a PRD aligned with existing decision logs. Use when user wants to create a PRD from the current context.
---

This skill takes the current conversation context and produces a PRD grounded in the product's existing decision history. Do NOT interview the user — synthesize what you already know.

## Process

1. Read the decision log files the user already has. Extract relevant prior decisions, constraints, and rationale that apply to this feature area. Use the product's domain vocabulary throughout the PRD.

2. Identify the key stakeholders and actors affected by this feature. Check with the user that you have the right ones before proceeding.

3. Write the PRD using the template below. Flag any section where you had to make assumptions due to gaps in the decision logs — mark those assumptions clearly so the user can validate them.

4. Save or share the PRD in whatever format the user prefers (document, file, paste).

<prd-template>

## Problem Statement

The problem that users or the business are facing, described from the customer's or stakeholder's perspective. Avoid solution language here.

## Strategic Alignment

How this feature connects to broader product goals, OKRs, or strategic bets. Reference any relevant prior decisions from the decision log that shaped or constrain this direction.

## Solution Overview

A plain-language description of the proposed solution. Focus on outcomes and the experience being created, not implementation mechanics.

## User Stories

A numbered list of user stories covering all meaningful scenarios. Each story follows the format:

1. As a <persona>, I want <capability>, so that <outcome/benefit>

<user-story-example>
1. As a product manager, I want to see a consolidated view of all open decisions, so that I can prioritize which ones need resolution before the next milestone.
</user-story-example>

Cover the primary flow, edge cases, error states, and any admin or operator needs. Be extensive — missing stories become missing requirements.

## Acceptance Criteria

A numbered checklist of conditions that must be true for this feature to be considered done. Written as observable outcomes, not implementation steps.

1. Given <context>, when <action>, then <expected result>

## Product Decisions

Key decisions made in scoping this PRD. Include:

- Scope boundaries and what was deliberately included or excluded
- Prioritization trade-offs and the reasoning behind them
- Assumptions about user behavior or market conditions
- Dependencies on other teams, vendors, or product areas
- Open questions that remain unresolved and who owns answering them

Reference relevant entries from the decision log where applicable.

## Out of Scope

Explicitly list what is NOT being addressed in this PRD and, where useful, why. This prevents scope creep and sets clear expectations with stakeholders.

## Success Metrics

How success will be measured. Include:

- Primary metric(s) that define success
- Guardrail metrics (things that must not regress)
- How and when these will be measured

## Further Notes

Any additional context, risks, dependencies, or open questions that did not fit elsewhere.

</prd-template>
