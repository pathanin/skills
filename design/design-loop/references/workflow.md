# Running Phase 4 as a workflow

Phases 1 to 3 stay inline: the interview needs the user, preflight needs the user, and `bar.md` has to be shown before anything is built. Only Phase 4 becomes a workflow — scout inline, then fan out.

## Why a workflow rather than loose subagents

Three of this skill's rules are exhortations when you fan out by hand, and structural facts when you fan out in a script:

- **Binary verdicts, not scores.** The verdict schema has a boolean. A critic that wants to hedge cannot; the tool layer rejects it and makes it retry.
- **All three must pass.** `!silent.length && !failing.length` is arithmetic, not judgment. Nothing talks itself into shipping a piece on two out of three, and a critic that never reported fails closed rather than counting as a yes.
- **Critics need fresh context.** Separate `agent()` calls cannot see the builder's reasoning, because there is no channel through which they could.

A workflow also makes the loop bounded. `MAX_ROUNDS` is 3: a budget ceiling, not a target, with the budget guard stopping a round that cannot be paid to finish. Do not turn either into a cost report — the point is that the run terminates and says what it left unresolved, not that you quote a number at the user.

Invoking `/design-loop` is itself the opt-in that authorizes calling Workflow. Say so when you launch it; do not make the user type "ultracode".

## Shape

Rounds are the outer loop; pieces run in `parallel` inside each round. This is a barrier, deliberately: the merge agent needs one coherent snapshot of every piece's latest build, and it cannot get that if piece A is on round 3 while piece B is on round 1.

An earlier version of this skill pipelined pieces so a fast one never waited. That traded away the merge step, and at a 3-round cap the idle cost is three waits — far cheaper than a round spent re-fixing what another builder already fixed.

Inside one round the three critics are also a barrier, for the older reason: the pass decision needs all of them.

## Script

Pass `bar.md`, the design system, and the pieces in via `args` — do not have agents re-read files you already have. Each piece is `{name, brief, mechanisms}`, where `mechanisms` is the subset of `bar.md` that applies to that piece as a single string — the same prose you showed the user, minus the lines another piece owns. Interpolating an array here silently comma-joins it. The whole bar goes to no one.

```js
export const meta = {
  name: 'design-loop',
  description: 'Build each piece, merge, and loop past three critics until all agree it beats the bar',
  phases: [
    { title: 'Build', detail: 'one builder per unwon piece per round' },
    { title: 'Merge', detail: 'reconcile the shared surface, emit settled decisions' },
    { title: 'Critique', detail: 'brief, system and craft critics, fresh context' },
  ],
}

const VERDICT = {
  type: 'object',
  properties: {
    pass: { type: 'boolean', description: 'true only if this beats the bar, not if it is close' },
    biggest_gap: { type: 'string', description: 'the single largest remaining gap, one sentence' },
  },
  required: ['pass', 'biggest_gap'],
}

const MERGE = {
  type: 'object',
  properties: {
    settled: { type: 'string', description: 'decisions now fixed across pieces; conform, do not re-decide' },
    conflicts: { type: 'string', description: 'anything reconciled that a builder should know it lost' },
  },
  required: ['settled'],
}

const { pieces, designSystem, goal } = args   // each piece carries its own .mechanisms
const MAX_ROUNDS = 3          // budget ceiling per piece, always applies
const FLOOR = 60_000          // do not start a round we cannot afford to finish

const criticNames = ['brief', designSystem && 'system', 'craft'].filter(Boolean)
const state = new Map(pieces.map(p => [p.name, { gaps: [], history: [], won: false, rounds: 0 }]))
let settled = ''

for (let round = 1; round <= MAX_ROUNDS; round++) {
  const active = pieces.filter(p => !state.get(p.name).won)
  if (!active.length) break
  if (budget.total && budget.remaining() < FLOOR) {
    log(`out of budget at round ${round}, ${active.length} pieces unresolved`)
    break
  }

  // 1. Build. Every active piece, blind to every other one.
  const builds = await parallel(active.map(piece => () => {
    const { gaps } = state.get(piece.name)
    const last = gaps[gaps.length - 1]
    return agent(
      `${piece.brief}\n\nGoal: ${goal}\nRound ${round}.` +
      (settled ? `\n\nAlready settled across the whole build — conform to these, do not re-decide them:\n${settled}` : '') +
      (last ? `\n\nFix this first: ${last.primary}` +
              (last.secondary ? `\nDo not regress these while you do: ${last.secondary}` : '') : ''),
      { label: `build ${piece.name} r${round}`, phase: 'Build' }
    )
  }))

  // 2. Merge. Skipped when there is nothing to reconcile against.
  if (active.length > 1) {
    const merged = await agent(
      `Reconcile the work below into one coherent artefact. Collapse decisions the builders made ` +
      `independently and duplicately — keep the better one, edit the shared files in place, and leave ` +
      `each piece's own work alone. Do not improve anything; you are unifying, not building.\n\n` +
      `Then return the decisions that are now fixed across pieces, so no builder re-decides them next round.\n\n` +
      active.map((p, i) => `# ${p.name}\n${builds[i]}`).join('\n\n'),
      { label: `merge r${round}`, phase: 'Merge', model: 'sonnet', schema: MERGE }
    )
    settled = merged?.settled || settled
  }

  // 3. Critique. The merged state is this round's build for every piece.
  await parallel(active.map((piece, i) => async () => {
    // The merge agent edited shared files in place, so the artefact under judgment is on
    // disk, not in builds[i]. Say so, or the critics grade a pre-merge string.
    const build = builds[i] + (settled
      ? `\n\n(Reconciled in the merge step — judge the current state on disk, not this text.` +
        `\nSettled across pieces: ${settled})`
      : '')
    const critics = [
      { name: 'brief', run: () => agent(
        `Judge ONLY whether this does the thing it set out to do: ${piece.brief}\n` +
        `Ignore aesthetics entirely. Be harsh; praise is not useful.\n\n${build}`,
        { label: `brief ${piece.name}`, phase: 'Critique', model: 'sonnet', schema: VERDICT }
      ) },
      designSystem && { name: 'system', run: () => agent(
        `Check this against the design system below. Mechanical adherence only.\n\n` +
        `# Design system\n${designSystem}\n\n# Output\n${build}`,
        { label: `system ${piece.name}`, phase: 'Critique', model: 'haiku', effort: 'low', schema: VERDICT }
      ) },
      { name: 'craft', run: () => agent(
        `Render this output and put it beside the reference with the labels stripped, so you do not ` +
        `know which is ours. Say which is better. Then check it against the mechanisms below, and ` +
        `only those — they are this piece's scope. Do not fail it for anything else the reference ` +
        `does; that is another piece's job.\n` +
        `Judge the rendered result, never the code — reading the implementation makes you grade intent ` +
        `instead of what actually came out.\n\n# The bar\n${piece.mechanisms}\n\n# Output\n${build}`,
        { label: `craft ${piece.name}`, phase: 'Critique', model: 'opus', effort: 'high', schema: VERDICT }
      ) },
    ].filter(Boolean)

    // parallel() preserves order, so index i is critics[i] even when one returns null
    const verdicts = await parallel(critics.map(c => c.run))
    const silent = critics.filter((c, i) => !verdicts[i]).map(c => c.name)
    const failing = critics
      .map((c, i) => ({ critic: c.name, gap: verdicts[i]?.biggest_gap }))
      .filter((r, i) => verdicts[i] && !verdicts[i].pass)

    const st = state.get(piece.name)
    st.rounds = round

    if (!silent.length && !failing.length) {
      st.won = true
      log(`${piece.name}: won on round ${round}`)
      return
    }

    st.history.push({ round, failing, silent })

    // One primary gap: if it does not do the job, nothing else matters yet; the bar
    // comes before house style. At three rounds the others ride along as do-not-regress
    // lines rather than being dropped — there is no later round to raise them in.
    const order = ['brief', 'craft', 'system']
    const ranked = failing.sort((a, b) => order.indexOf(a.critic) - order.indexOf(b.critic))
    st.gaps.push({
      primary: ranked[0] ? `${ranked[0].critic}: ${ranked[0].gap}` : `no verdict from ${silent.join(', ')}`,
      secondary: ranked.slice(1).map(r => `${r.critic}: ${r.gap}`).join('; '),
    })
    log(`${piece.name} r${round}: ${st.gaps[st.gaps.length - 1].primary}`)
  }))
}

const results = pieces.map(p => {
  const st = state.get(p.name)
  if (st.won) return { piece: p.name, won: true, rounds: st.rounds, history: st.history }

  const last = st.history[st.history.length - 1]
  const stuck = criticNames.filter(n =>
    st.history.length && st.history.every(h =>
      h.failing.some(f => f.critic === n) || h.silent.includes(n)))

  // A critic that never reported blocks the piece just as hard as one that failed it,
  // so name both — otherwise the handback reads "nothing failing" on a piece that never ran.
  const blockers = last
    ? [...last.failing.map(f => f.critic), ...last.silent.map(n => `${n} (no verdict)`)]
    : []
  log(`${p.name}: unresolved after ${st.history.length} rounds — blocked by ${blockers.join(', ') || 'nothing recorded'}`)

  return {
    piece: p.name,
    won: false,
    rounds: st.history.length,
    history: st.history,
    outstanding: last ? last.failing : [],   // what to fix next, per critic
    silent: last ? last.silent : [],         // critics that never reported
    stuck,                                   // failed or stayed silent every round
  }
})

const unresolved = results.filter(r => !r.won)
if (unresolved.length) {
  log(`${unresolved.length}/${results.length} pieces unresolved: ${unresolved.map(r => r.piece).join(', ')}`)
}
return { results, unresolved, settled }
```

## Things that will bite you

- **A critic returning `null`** means it died or was skipped, not that it passed. The `silent` array is why a dead critic blocks the piece instead of silently letting it through — `!silent.length && !failing.length` is the pass condition, so a missing verdict fails closed.
- **Each piece gets only its own mechanisms.** `piece.mechanisms` is the slice of `bar.md` that applies here. Hand the craft critic the whole bar and it will fail a piece for work another piece is doing — a gap the builder cannot close without leaving its brief, so it repeats every round until the piece exhausts.
- **Render at the size the bar was captured at.** Chrome's `--screenshot` captures full page height, not `--window-size`, so a short section becomes a tall image with a lake of empty ground below it. The craft critic then grades that emptiness as a composition failure. Crop to the viewport, or expect whitespace complaints that are about your screenshot rather than the design.
- **A single component is the common case of that gotcha, not an edge one.** Crop to the element's own bounds, and for an interaction capture frames across the transition rather than one settled state — a still of a toggle shows the craft critic nothing about the motion it is being asked to judge.
- **`designSystem` being absent** drops the system critic to two, which is the honest outcome from Phase 2 — it does not invent a standard to have something to say.
- **Do not reach for `isolation: 'worktree'` on builders.** An earlier version of this skill did, to stop pieces colliding on shared files. With a merge step, collision is the design and merge is the resolver — isolating builders hides their work from the thing whose job is to reconcile it. Only isolate if a builder does something genuinely destructive to the tree.
- **The merge agent unifies, it does not build.** A merge agent that starts improving things becomes an unjudged fourth builder whose work no critic scoped. If merges keep returning substantive changes, the pieces are split wrong.
- **`settled` is the only channel between builders.** Keep it short and declarative — decisions, not context. Piping other pieces' output into a builder's prompt to "help it" unblinds it and the critics start grading a consensus rather than a piece.
- **Merge is skipped at one piece.** `active.length > 1` guards it; a merge agent with a single input is pure cost.
- **No `Date.now()`, `new Date()` or `Math.random()`** in workflow scripts — they throw, because they would break resume. Stamp times after the run returns.
- **Hitting `MAX_ROUNDS` is a result, not a silent stop.** A piece that ran out of rounds returns `won: false` with `outstanding` (what each critic still fails on) and `stuck` (critics that failed every round). A truncated run that reports nothing reads as a run that finished.
- **`stuck` is weaker at three rounds than it was at ten.** Failing 3/3 is often just noise; failing 10/10 was diagnostic. Read it as a pointer, and trust it only when the same gap comes back in near-identical words — that is the sign the builder cannot see what the critic sees, and the fix is the bar or the builder's inputs, not the round count.
- **One primary gap, the rest as do-not-regress.** Sending every failing critic's gap as work scatters the builder across changes that trade against each other; dropping them entirely wastes one of only three rounds. `primary` is the thing to fix, `secondary` is a list not to break, and `history` keeps the full picture for the handoff.
- **Resume after a script edit**: relaunch with `{scriptPath, resumeFromRunId}`. Everything before your first edit returns from cache, so fixing a critic's brief does not re-pay for the builds.
