## Working agreements
- Clarify scope before coding if ambiguous; otherwise, flag uncertainty and proceed or stop on blocking unknowns.
- Working by Goal-Driven Execution. it will be expanded in the next section.
- Ask targeted clarifying questions only when essential information is genuinely missing.
- Aim for one failure case and one boundary condition per function under test.
- Externalize deterministic subproblems to disposable scripts; reserve reasoning for ambiguous decisions. Skip tooling when inline is simpler.
- Report errors matter-of-factly: what failed, what you tried.

## Goal-Driven Execution
- Define success criteria; transform imperative tasks into verifiable goals
- **Track multi-step tasks in the to-do list.**
- Remember Eisenhower: plans are worthless, but planning is everything.

## Code Comments
Code comments should be genuinely concise — just enough to understand, and no longer than 1-2 sentences. Avoid verbosity or unnecessary historicizing when commenting. Comments should be clean, tight, functional, and present state oriented.

When leaving comments in code, especially during multiple rounds of edits, do not unnecessarily describe or historicize about defunct or past paths or a path or approach that was left behind. If there's a genuine risk of retracing an error, it's fine to point that out - otherwise hew towards present behavior and functionality / present state, not archaeology of past approaches. Clear that out and remove it where it's extraneous.

Comments follow the same prose rules as responses: short SVO declaratives, no verbless fragments, no 'not x but y', no colon-weighted sentences, no nominalizations.

## Git
- **Always commit at logical checkpoints**, don't ask. use concise git message.
- Imperative subject lines ("Add X", "Fix Y"); body only if needed.
- Ask first before force-pushing, rewriting history, or discarding uncommitted work.