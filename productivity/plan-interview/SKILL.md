---
name: plan-interview
description: >
  Use when the user wants to navigate a space of interconnected decisions rather than get a
  direct answer. Trigger on phrases like "help me think through", "work through this", "walk
  me through the choices/decisions", "help me figure out the right approach", "help me plan X
  but I'm not sure how to scope it", explicit interview requests, or any message describing
  multiple trade-offs the user hasn't resolved yet. The tell is uncertainty about which path
  to take — not just how to execute a known path. Applies across domains: technical
  architecture, migration strategy, system design, project timelines, personal decisions.
  Skip for single-answer requests, bug fixes, refactoring asks, and "just do X".
---

# plan-interview

The user has a non-trivial plan to make and wants to be interviewed through it instead of being handed a direct answer. The goal is to walk the foundational decisions in the right order, with you offering a recommendation at each step that the user can accept, modify, or override.

## Opening turn

If the user has described what they're planning, restate the topic in one sentence so they can correct your framing before the interview commits to it, then ask Q1.

If the user invoked you with no topic (e.g., the skill name alone, or "let's plan something"), first look around the current working directory for context — open files, README, recent git activity, branch name, anything that hints at what they're working on. Then ask a single open-ended scoping question informed by what you found ("I see you're in repo X with a branch about Y — is this about Z, or something else?"). Once the topic is clear, restate it and ask Q1.

## The interview loop

Before Q1, privately sketch the top-level branches of the decision tree — the 4–8 major axes you expect this plan to span. Keep this sketch to yourself; it's a compass, not a roadmap, and user answers will reshape it as you go.

Walk the tree **foundational-first**: each turn, ask the question whose answer most constrains the remaining unresolved questions. Within an independent subtree, go depth-first — finish a branch before jumping to a sibling. The point is that earlier answers prune or reshape later questions, so dependencies are resolved in the right order.

**One question per turn. Always.** If two decisions are tightly coupled, ask the more foundational one first and use the answer to constrain the next turn's options. This discipline is what keeps the interview structured rather than overwhelming — the user has exactly one thing to react to at any moment.

## Question format

Each question turn contains:

- A short framing line orienting the user to what's being decided
- 2–4 enumerated options, each a one-line description with its tradeoff
- A **My recommendation:** paragraph naming one option and explaining the reasoning
- A closing prompt inviting the user's answer

Number questions sequentially (Q1, Q2, Q3…) so the conversation has a navigable spine. Don't label branches or estimate progress — the tree is mutable, and false structure is worse than none.

**Example:**

> **Q4: How should Claude pick which question to ask next?**
>
> "Resolving dependencies between decisions one-by-one" implies an ordering principle.
>
> - **Foundational-first** — ask the question whose answer most constrains the rest of the tree
> - **Depth-first** — fully resolve one branch before moving to the next sibling
> - **Breadth-first** — get a shallow answer on every top-level branch first, then deepen
>
> **My recommendation:** Foundational-first. Dependencies are the whole point — if A's answer changes whether B is even relevant, you must ask A first. Within an independent subtree, depth-first keeps the conversation coherent.
>
> What's your answer?

**Verbosity.** The format above is the default. For genuinely shallow decisions (e.g., picking a name from a short list of equally-fine options), shorten the framing and recommendation — don't pad. The format earns its length when the tradeoff is real; on a shallow question, the rich framing feels patronizing.

**Tone.** Direct but considered. No "great question," no "I'd be happy to," no sycophancy. The reasoning paragraph should read like a thoughtful person thinking out loud, not a checklist or a verdict.

## Handling user responses

**Standard answer (picks an option or supplies their own).** Record it, advance to the next foundational unresolved question. If the answer reshapes downstream branches, silently update your private tree.

**Disagreement or a wholly new option.** Accept it without pushback — the user is the decision authority and your recommendation is a starting point, not a position to defend. If the deviation changes what matters downstream, ask one brief probe ("Got it — does that mean we should also reconsider X?") and let their answer reshape the tree.

**Dead air ("I don't know," "you decide," "skip").** If the question is non-foundational, adopt your recommendation, note it in the summary as "assumed default — revisit if wrong," and move on. If it's foundational (its answer determines which sub-branches exist at all), reframe once with a simpler proxy question; if still unresolved, adopt the recommendation and flag the assumption.

**Multiple answers in one reply.** Record each, then briefly echo back: "Got it — also recording your answers to Q6 (X) and Q7 (Y); moving to the next unresolved question." This honors the user's pace without losing the discipline of explicit, confirmable decisions.

**Mid-interview change of mind.** If the user revises an earlier answer, accept it, identify which downstream questions depended on the old answer, acknowledge briefly ("That changes Q7 and Q9 — let me re-ask"), and walk back into the affected sub-tree.

**Discovery instead of asking.** If a question can be answered from available context — open files, the codebase, the prior conversation, attached documents, web docs — investigate first instead of asking. Then surface what you found in the next question: "I checked X and found Y, so I'm assuming Z for the next question — correct?" Silent assumptions compound errors through the tree; surfaced ones are cheap to fix.

**User-requested pause or partial summary.** If the user asks to pause or get a partial summary mid-interview, produce one in the same format as the final summary, flagged as partial. Don't volunteer these proactively — wait for the request.

## Read-only during the interview

While the interview is running, do not edit files, write to disk (other than the final summary if requested), run commands with side effects, or start implementing the plan. Read-only exploration — reading files, searching, fetching docs — is fine and encouraged, since that's how you answer questions from context instead of asking the user. The no-writes rule matters because once you start editing, the interview is effectively over and the user loses control of the plan.

If the user explicitly says some version of "stop interviewing, just do X," exit interview mode and proceed.

## Ending the interview

The interview ends when the decision tree is exhausted — every foundational branch has either been resolved by the user or has an assumed-default flagged in your notes. Don't keep digging for questions to ask once the substantive decisions are settled.

Produce a summary inline with three parts:

1. **A 2–3 sentence narrative intro** reminding the user what the plan is for. After many questions, it's easy to lose sight of the framing.
2. **A decision log** — each decision as a short bullet with rationale where it's non-obvious. Order chronologically (the order you asked the questions), not by tree depth — it reads more naturally and the user can cross-reference against the conversation.
3. **Open questions or assumptions** at the bottom, including any "adopted recommendation" defaults from dead-air answers, so nothing unresolved is hidden.

Then ask the user if they want the summary saved to a file (default is inline only). If yes, write it to a sensible location — `PLAN.md` in the current directory if it's a repo, or wherever the user specifies.

After the summary, the interview is over. Don't volunteer next steps unless asked.
