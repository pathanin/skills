# Running the loop as a workflow

Intake, context, and preflight stay inline. Only the loop runs as a workflow.

## Why a workflow rather than loose subagents

When you fan out by hand, the skill's rules are things to remember. In a script they are structure:

- **Every critic must pass.** `!silent.length && !failing.length` is arithmetic. Nothing talks itself into stopping on two out of three, and a critic that never reported fails closed.
- **A blocking issue beats a score.** `pass` is computed in the script from `score >= MIN_SCORE && !blocking.length`. A critic cannot return a pass that contradicts its own blocking list.
- **Critics judge cold.** Each critic is a separate `agent()` call, and its prompt never includes earlier scores or history. With no channel to see its own last score, it cannot anchor on it.
- **The loop is bounded.** `MAX_ROUNDS` comes from the user. The budget guard stops a round that cannot be paid to finish.

Invoking `/critic-loop` is itself the opt-in that authorizes calling Workflow. Say so when you launch it.

## Shape

The rounds run one at a time. Within a round, the builder runs first, then every critic in `parallel`. That is a barrier on purpose, because the stop decision needs every verdict. There is one builder, so there are no pieces and no merge step.

## Args

Pass everything in via `args`. Do not have agents re-read files you already have.

```js
{
  goal: 'the user request, verbatim',
  context: '<contents of context.md, or empty string for greenfield>',
  minScore: 8,
  maxRounds: 3,
  critics: [
    // one per critic that survived preflight; `brief` is the per-run brief you wrote
    { name: 'brief', brief: '...', model: 'sonnet' },
    { name: 'consistency', brief: '...', model: 'sonnet', readsCode: true },
    { name: 'craft', brief: '...', model: 'opus', effort: 'high' },
  ],
  render: 'how to render the output: command, URL, viewport, crop, frames',
}
```

Every text field is a string. If you interpolate an array into a prompt, it is silently comma-joined.

## Script

```js
export const meta = {
  name: 'critic-loop',
  description: 'One builder revises against fresh-context critics until every critic clears the score floor with no blocking issues',
  phases: [
    { title: 'Build', detail: 'one builder, works in place from project context' },
    { title: 'Critique', detail: 'every critic in parallel, fresh context, anchored rubric' },
  ],
}

const VERDICT = {
  type: 'object',
  properties: {
    score: { type: 'integer', minimum: 0, maximum: 10, description: 'anchored rubric; 8 means shippable with only nits' },
    blocking: {
      type: 'array',
      items: { type: 'string' },
      description: 'issues an expert would reject the work for, one sentence each; empty only if none',
    },
    biggest_gap: { type: 'string', description: 'the single change that would raise the score most, one sentence' },
  },
  required: ['score', 'blocking', 'biggest_gap'],
}

const RUBRIC =
  `Score on this rubric, not on effort or improvement:\n` +
  `10 nothing a demanding expert would change\n8 shippable, only nits left\n` +
  `6 works, but an expert would send it back\n4 major problems\n2 misses the goal or is broken\n\n` +
  `List every blocking issue: anything an expert would reject the work for. A high score does not ` +
  `excuse a blocking issue. List it anyway. Be harsh; praise is not useful.`

const { goal, context, critics, render } = args
const MIN_SCORE = args.minScore
const MAX_ROUNDS = args.maxRounds
const FLOOR = 60_000   // do not start a round we cannot afford to finish

// Feedback order: if it does not do the job, nothing else matters yet; craft comes last.
const rank = name => name === 'brief' ? 0 : name === 'consistency' ? 1 : name === 'craft' ? 3 : 2

const history = []      // per round: { round, verdicts: [{critic, score, blocking, gap}], silent }
let report = ''         // builder's last report: what it built, files touched, how to render
let feedback = ''
let passed = false

for (let round = 1; round <= MAX_ROUNDS; round++) {
  if (budget.total && budget.remaining() < FLOOR) {
    log(`out of budget before round ${round}`)
    break
  }

  // 1. Build. Works in place; only the critics' feedback and its own last report come back to it.
  report = await agent(
    `Goal: ${goal}\nRound ${round} of at most ${MAX_ROUNDS}.\n\n` +
    (context
      ? `Stay consistent with this project. These conventions were read from the codebase. ` +
        `Reuse what exists before adding anything new:\n${context}`
      : `The project is empty. Build from the request alone and choose conventions deliberately.`) +
    (report ? `\n\nYour report from last round:\n${report}` : '') +
    (feedback ? `\n\nCritics' feedback, highest priority first. Fix the blocking issues in order, then the gaps:\n${feedback}` : '') +
    `\n\nReturn a short report: what you built or changed, the files touched, and how to render it. ` +
    `Do not argue with the feedback or grade your own work.`,
    { label: `build r${round}`, phase: 'Build' }
  ) || report

  // 2. Critique. Each critic gets the goal, its brief, and how to see the output. It never gets history.
  const verdicts = await parallel(critics.map(c => () => agent(
    `${c.brief}\n\nThe goal was: ${goal}\n\n` +
    (c.readsCode
      ? `Judge against these project conventions, and only these:\n${context}\n\n` +
        `Read the diff (git diff, plus untracked files) and the rendered output. A convention ` +
        `the project does not state is not a blocking issue.\n\n`
      : `Judge the rendered result, never the code. Reading the implementation makes you grade intent ` +
        `instead of what actually came out.\n\n`) +
    `How to render it: ${render}\n\nBuilder's report (for locating files, not evidence of quality):\n${report}\n\n${RUBRIC}`,
    { label: `${c.name} r${round}`, phase: 'Critique', model: c.model, effort: c.effort, schema: VERDICT }
  )))

  // parallel() preserves order, so verdicts[i] is critics[i] even when one returns null
  const silent = critics.filter((c, i) => !verdicts[i]).map(c => c.name)
  const results = critics
    .map((c, i) => verdicts[i] && {
      critic: c.name, score: verdicts[i].score, blocking: verdicts[i].blocking, gap: verdicts[i].biggest_gap,
      pass: verdicts[i].score >= MIN_SCORE && !verdicts[i].blocking.length,
    })
    .filter(Boolean)
  const failing = results.filter(r => !r.pass).sort((a, b) => rank(a.critic) - rank(b.critic))

  history.push({ round, verdicts: results, silent })
  log(`r${round}: ` + results.map(r => `${r.critic} ${r.score}${r.blocking.length ? `/${r.blocking.length} blocking` : ''}`).join(', ') +
      (silent.length ? `; no verdict from ${silent.join(', ')}` : ''))

  if (!silent.length && !failing.length) {
    passed = true
    break
  }

  feedback = [
    ...failing.flatMap(r => r.blocking.map(b => `BLOCKING (${r.critic}): ${b}`)),
    ...failing.filter(r => r.score < MIN_SCORE).map(r => `GAP (${r.critic}, scored ${r.score}/${MIN_SCORE}): ${r.gap}`),
  ].join('\n')
}

const last = history[history.length - 1]
const recurring = []
if (!passed && history.length > 1) {
  // A blocking issue reported in every round is the sign the builder cannot see what the critic sees.
  for (const c of critics) {
    const rounds = history.map(h => h.verdicts.find(v => v.critic === c.name))
    if (rounds.every(v => v && v.blocking.length)) recurring.push({ critic: c.name, each_round: rounds.map(v => v.blocking) })
  }
}
if (!passed) log(`unresolved after ${history.length} rounds`)

return {
  passed,
  rounds: history.length,
  final: last ? last.verdicts : [],
  silent: last ? last.silent : [],
  scores: critics.map(c => ({ critic: c.name, by_round: history.map(h => h.verdicts.find(v => v.critic === c.name)?.score ?? null) })),
  recurring,
  report,
}
```

## Things that will bite you

- **A critic returning `null`** means it died or was skipped, not that it passed. `silent` blocks the stop, so a dead critic fails closed.
- **Never pipe `history` into a critic prompt.** That is the drift channel. A critic that sees "you gave 7 last round" gives 8 this round for the same work.
- **`minScore: 0` is blocking-only mode.** Every score is at least 0, so only the blocking lists decide. That is intended, not a bug.
- **An empty `blocking` array with a low score is still a fail.** The builder gets `biggest_gap` for that critic instead. If it plateaus there round after round, the floor may be above what the critic will award. Report that rather than raising the cap.
- **Only the consistency critic reads code** (`readsCode: true`). Give it to craft and craft grades intent instead of result.
- **Greenfield drops consistency.** With `context` empty, leave the consistency critic out of `critics` entirely. Do not pass it an empty convention list and hope it abstains.
- **Render at the output's real size.** Chrome's `--screenshot` captures full page height, not `--window-size`. Crop to the viewport or to the component's own bounds. For an interaction, capture frames across the transition, not one settled state.
- **The builder works in place, without `isolation: 'worktree'`.** There is one builder and the critics need to see its work on disk.
- **No `Date.now()`, `new Date()` or `Math.random()`** in workflow scripts. They throw, because they would break resume.
- **Running out of rounds is a result.** `passed: false` comes back with `final`, `scores`, and `recurring`. Report it as unresolved. A truncated run that reports nothing reads as a run that finished.
- **Resume after a script edit**: relaunch with `{scriptPath, resumeFromRunId}`. Everything before your first edit returns from cache.
