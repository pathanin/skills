# Running the loop as a workflow

Intake, context, and preflight stay inline. Only the loop runs as a workflow.

## Why a workflow rather than loose subagents

When you fan out by hand, the skill's rules are things to remember. In a script they are structure:

- **Every critic must pass.** `!silent.length && !failing.length` is arithmetic. Nothing talks itself into stopping on two out of three, and a critic that never reported fails closed.
- **A blocking issue beats a score.** The script computes `pass`: no blocking issues, plus `score >= MIN_SCORE` for scored critics. A critic cannot return a pass that contradicts its own blocking list.
- **Blocking means something different per role.** `BLOCKING_RULE` gives brief, consistency, and everything else its own definition. With one shared "anything an expert would reject" rule, a fresh craft critic found new blockers in every round of every test run and never passed, while consistency filed a real convention breach as a nit.
- **Critics judge cold.** Each critic is a separate `agent()` call. Its prompt never includes earlier scores, feedback, or the builder's summary, which by round 2 reads "fixed what the critic raised". Critics get only the files touched, how to render them, and the settled decisions. With no channel to its last score, a critic cannot anchor on it.
- **The builder holds the memory.** Critics are cold, so only the builder can tell a deliberate trade-off from a mistake. It sees every round's feedback and may decline an item that reverses an earlier requested change or goes beyond the goal. Each decline reaches later critics as a settled decision, with its reason and no score. Without this, a test run flip-flopped: round 1's critic asked for Pro first on mobile, and round 2's critic blocked that same change.
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
  minScore: 7,
  maxRounds: 3,
  critics: [
    // one per critic that survived preflight; `brief` is the per-run brief you wrote
    // scored defaults to false for brief and consistency, true for everything else
    { name: 'brief', brief: '...', model: 'sonnet' },
    { name: 'consistency', brief: '...', model: 'sonnet', readsCode: true },
    // extra lenses: { name: 'a11y', brief: '...', model: 'sonnet', scored: false,
    //                 blockingRule: 'Blocking means a WCAG 2.2 AA failure, with the criterion number.' }
    { name: 'craft', brief: '...', model: 'opus', effort: 'high' },
  ],
  render: 'how to render the output: command, URL, viewport, crop, frames',
  base: '<git rev-parse HEAD from preflight, or empty string if not a repo or no commits yet>',
}
```

`minScore` and `maxRounds` default to 7 and 3 if left out. An extra critic without `blockingRule` gets the default rule: a defect a user would actually hit, with evidence. Every text field is a string. If you interpolate an array into a prompt, it is silently comma-joined.

## Script

```js
export const meta = {
  name: 'critic-loop',
  description: 'One builder revises against fresh-context critics until every critic passes: no blocking issues, and scored critics at or above the floor',
  phases: [
    { title: 'Build', detail: 'one builder, works in place from project context' },
    { title: 'Critique', detail: 'every critic in parallel, fresh context, per-role blocking rule' },
  ],
}

const BUILD = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: 'what you built or changed this round and why; only you see this' },
    files: { type: 'array', items: { type: 'string' }, description: 'every file created or modified, repo-relative' },
    render: { type: 'string', description: 'how to see the result now, if it differs from the standing instructions' },
    declined: {
      type: 'array',
      items: {
        type: 'object',
        properties: { issue: { type: 'string' }, reason: { type: 'string' } },
        required: ['issue', 'reason'],
      },
      description: 'feedback you deliberately did not act on this round, each with the reason; empty if none',
    },
  },
  required: ['summary', 'files', 'render', 'declined'],
}

const BLOCKING_LIST = {
  type: 'array',
  items: { type: 'string' },
  description: 'blocking issues under the rule above, one sentence each with its evidence; empty only if none',
}
const BINARY = {
  type: 'object',
  properties: {
    blocking: BLOCKING_LIST,
    biggest_gap: { type: 'string', description: 'the most useful non-blocking improvement, one sentence' },
  },
  required: ['blocking', 'biggest_gap'],
}
const SCORED = {
  type: 'object',
  properties: {
    score: { type: 'integer', minimum: 0, maximum: 10, description: 'anchored rubric; 8 means good, ships as is' },
    blocking: BLOCKING_LIST,
    biggest_gap: { type: 'string', description: 'the single change within the goal that would raise the score most, one sentence' },
  },
  required: ['score', 'blocking', 'biggest_gap'],
}

// Anchored on what you can observe, not on "a demanding expert": an expert can always name a change,
// so the old anchors put 8+ out of reach and craft scored 6-7 in all 12 test verdicts, blockers or not.
const RUBRIC =
  `Score the work as it is now, on this rubric, not on effort or improvement:\n` +
  `10 you would hold it up as the example of how to do this\n9 excellent, only nits you would mention in passing\n` +
  `8 good, ships as is; the gaps left are worth doing but not needed\n` +
  `7 solid, but one clear gap you would fix before shipping\n6 works, but you would send it back\n` +
  `4 major problems\n2 misses the goal or is broken\n` +
  `Be accurate, not harsh: a score too low is as wrong as a score too high. Below 8, biggest_gap names what stops it shipping.\n\n`

// What counts as blocking, per role. A shared "anything an expert would reject" rule let craft
// re-sample new blockers every round and let consistency file real breaches as nits.
const BLOCKING_RULE = {
  brief: `Blocking means a stated requirement of the goal is not met, and you showed it by running or looking. ` +
    `Anything the goal does not ask for is at most a gap, never blocking.`,
  consistency: `Blocking means the change breaks a line on the conventions list; quote the line. Any clear breach of a ` +
    `listed convention is always blocking, however small. Anything not on the list is never blocking. If you have to ` +
    `interpret the line to decide whether it applies, it is a gap, not blocking: name the ambiguous line in biggest_gap.`,
}
const DEFAULT_RULE = `Blocking means a defect a user of this output would actually hit on realistic use for this goal ` +
  `(the input, audience, and screens the goal implies), with evidence: a measurement, a reproduction, or the exact screen ` +
  `region. A contrived edge case, taste, preference, polish, and features the goal did not ask for are gaps, not blocking.`

const { goal, context, render, base } = args
const MIN_SCORE = args.minScore ?? 7
const MAX_ROUNDS = args.maxRounds ?? 3
const FLOOR = 60_000   // do not start a round we cannot afford to finish
// Brief and consistency are yes/no jobs; a 10-point scale on them plateaus below any high floor.
const critics = args.critics.map(c => ({ ...c, scored: c.scored ?? !['brief', 'consistency'].includes(c.name) }))

// Feedback order: if it does not do the job, nothing else matters yet; craft comes last.
const rank = name => name === 'brief' ? 0 : name === 'consistency' ? 1 : name === 'craft' ? 3 : 2

const history = []      // per round: { round, verdicts: [{critic, score, blocking, gap, pass}], silent }
const feedbackLog = []  // every round's feedback, for the builder only
const settled = []      // builder's declines: { round, issue, reason }; critics see these as decisions
let build = null        // builder's last BUILD; critics get .files and .render, never .summary
let passed = false

for (let round = 1; round <= MAX_ROUNDS; round++) {
  if (budget.total && budget.remaining() < FLOOR) {
    log(`out of budget before round ${round}`)
    break
  }

  // 1. Build. Works in place; gets every round's feedback and its own last summary.
  const next = await agent(
    `Goal: ${goal}\nRound ${round} of at most ${MAX_ROUNDS}.\n\n` +
    (context
      ? `Stay consistent with this project. These conventions were read from the codebase. ` +
        `Reuse what exists before adding anything new:\n${context}`
      : `The project is empty. Build from the request alone and choose conventions deliberately.`) +
    `\n\nHow the critics will see your output; use the same way to check your own work before you finish:\n${render}` +
    (build ? `\n\nYour summary from last round:\n${build.summary}` : '') +
    (feedbackLog.length ? `\n\nCritics' feedback so far, oldest first. The last round is what to act on now:\n${feedbackLog.join('\n\n')}` : '') +
    `\n\nFix BLOCKING items in order. GAP items are optional: take one only if it stays inside the goal. ` +
    `Never add features, flags, or options the goal did not ask for.\n` +
    `You may decline a feedback item that reverses a change an earlier round asked for, or that goes beyond ` +
    `the goal. List each in \`declined\` with the reason; it is shown to the next critics as a settled decision. ` +
    `Do not decline something just because it is hard.\n` +
    `Leave your changes uncommitted in the working tree; the critics diff against the starting commit. ` +
    `Do not grade your own work.`,
    { label: `build r${round}`, phase: 'Build', schema: BUILD }
  )
  if (!next) log(`builder returned nothing in round ${round}; critics re-judge the previous state`)
  build = next || build
  if (next) settled.push(...next.declined.map(d => ({ round, ...d })))
  const files = build ? build.files.join('\n') : '(unknown)'
  const howToRender = render + (build && build.render ? `\n${build.render}` : '')
  const decisions = settled.length
    ? `Settled trade-offs. The builder kept these on purpose. Do not block on one unless you can show a defect ` +
      `its reason does not account for:\n${settled.map(d => `- ${d.issue} (kept because: ${d.reason})`).join('\n')}\n\n`
    : ''

  // 2. Critique. Each critic gets the goal, its brief, the files, and settled decisions. Never scores or feedback.
  const verdicts = await parallel(critics.map(c => () => agent(
    `${c.brief}\n\nThe goal was: ${goal}\n\n` +
    (c.name === 'consistency' ? `The conventions list. Judge against these, and only these:\n${context}\n\n` : '') +
    (c.readsCode
      ? `Read the change (${base ? `git diff ${base} -- <files>` : 'the files'}, plus any of them that are ` +
        `untracked) and the rendered output.\n\n`
      : `Judge the rendered result, never the code. Reading the implementation makes you grade intent ` +
        `instead of what actually came out.\n\n`) +
    `Files changed:\n${files}\n\nHow to render it: ${howToRender}\n\n${decisions}` +
    (c.scored ? RUBRIC : '') +
    `${c.blockingRule || BLOCKING_RULE[c.name] || DEFAULT_RULE} Apply that rule strictly; praise is not useful.`,
    { label: `${c.name} r${round}`, phase: 'Critique', model: c.model, effort: c.effort, schema: c.scored ? SCORED : BINARY }
  )))

  // parallel() preserves order, so verdicts[i] is critics[i] even when one returns null
  const silent = critics.filter((c, i) => !verdicts[i]).map(c => c.name)
  const results = critics
    .map((c, i) => verdicts[i] && {
      critic: c.name, scored: c.scored, score: c.scored ? verdicts[i].score : null,
      blocking: verdicts[i].blocking, gap: verdicts[i].biggest_gap,
      pass: !verdicts[i].blocking.length && (!c.scored || verdicts[i].score >= MIN_SCORE),
    })
    .filter(Boolean)
  const failing = results.filter(r => !r.pass).sort((a, b) => rank(a.critic) - rank(b.critic))

  history.push({ round, verdicts: results, silent })
  log(`r${round}: ` + results.map(r => `${r.critic} ${r.scored ? r.score : (r.pass ? 'pass' : 'fail')}` +
      `${r.blocking.length ? `/${r.blocking.length} blocking` : ''}`).join(', ') +
      (silent.length ? `; no verdict from ${silent.join(', ')}` : ''))

  if (!silent.length && !failing.length) {
    passed = true
    break
  }

  feedbackLog.push(`Round ${round}:\n` + [
    ...failing.flatMap(r => r.blocking.map(b => `BLOCKING (${r.critic}): ${b}`)),
    ...failing.filter(r => r.scored && r.score < MIN_SCORE).map(r => `GAP (${r.critic}, scored ${r.score}/${MIN_SCORE}, optional): ${r.gap}`),
  ].join('\n'))
}

// Same issue across rounds, by word overlap. A critic blocking every round on *different* issues is churn,
// a different failure: its blocking rule is too loose, not the builder too blind.
// ponytail: word-overlap similarity, misfires on short issues sharing domain words; use an agent judge if it matters.
const words = t => new Set(t.toLowerCase().match(/[a-z0-9]{4,}/g) || [])
const similar = (a, b) => {
  const A = words(a), B = words(b)
  const shared = [...A].filter(w => B.has(w)).length
  return Math.min(A.size, B.size) > 0 && shared / Math.min(A.size, B.size) >= 0.6
}
const last = history[history.length - 1]
const recurring = [], churning = []
if (!passed && history.length > 1) {
  for (const c of critics) {
    const rounds = history.map(h => h.verdicts.find(v => v.critic === c.name))
    if (!rounds.every(v => v && v.blocking.length)) continue
    const same = rounds[rounds.length - 1].blocking.filter(issue =>
      rounds.slice(0, -1).every(v => v.blocking.some(b => similar(b, issue))))
    if (same.length) same.forEach(issue => recurring.push({ critic: c.name, issue }))
    else churning.push(c.name)
  }
}
// Blockers first raised in the final round never reached the builder, so it could neither fix nor decline them.
const lastRoundNew = !passed && last ? last.verdicts.flatMap(v => v.blocking
  .filter(issue => !history.slice(0, -1).some(h => h.verdicts.some(e => e.critic === v.critic && e.blocking.some(b => similar(b, issue)))))
  .map(issue => ({ critic: v.critic, issue }))) : []
if (!passed) log(`unresolved after ${history.length} rounds`)

return {
  passed,
  rounds: history.length,
  final: last ? last.verdicts : [],
  silent: last ? last.silent : [],
  scores: critics.filter(c => c.scored).map(c => ({ critic: c.name, by_round: history.map(h => h.verdicts.find(v => v.critic === c.name)?.score ?? null) })),
  recurring,   // same issue every round: the builder cannot see what the critic sees
  churning,    // blocked every round, never on the same issue: the blocking rule is too loose
  lastRoundNew, // first raised in the final round: the user decides, the builder never saw them
  declined: settled,
  files: build ? build.files : [],
  summary: build ? build.summary : '',
}
```

## Things that will bite you

- **A critic returning `null`** means it died or was skipped, not that it passed. `silent` blocks the stop, so a dead critic fails closed.
- **Never pipe `history` or `feedbackLog` into a critic prompt.** That is the drift channel. A critic that sees "you gave 7 last round" gives 8 this round for the same work. `settled` is the one exception: it carries decisions and reasons, never scores.
- **Scores are only for judgment calls.** Brief and consistency are yes/no jobs. On a 10-point scale, a brief critic that had confirmed every requirement still sat at 8 with no blocking issues for three rounds against a floor of 9. Leave them `scored: false`.
- **Gaps are optional.** The builder used to get every under-floor gap as work, and a CSV tool picked up exact-decimal parsing, a `--max-distinct` flag, and a streaming memory model nobody asked for. Gaps from binary critics are never sent. Gaps from scored critics are marked optional and limited to the goal.
- **`minScore: 0` is blocking-only mode.** Every score is at least 0, so only the blocking lists decide. That is intended, not a bug.
- **The rubric is anchored on observable quality, and critics score accurately, not harshly.** The old anchors measured against "a demanding expert", who can always name a change, and every critic was told to be harsh. Craft scored 6 or 7 in all 12 test verdicts, including rounds with zero blocking issues. If craft still never clears 7 on good work, the score carries no signal, and craft should go pass/fail like the others.
- **An empty `blocking` array with a low score is still a fail** for a scored critic. The builder gets `biggest_gap` for that critic instead. If it plateaus there round after round, the floor may be above what the critic will award. Report that rather than raising the cap.
- **`lastRoundNew`** lists blockers first raised in the final round. The builder never saw them, so it could neither fix nor decline them. They go to the user to decide, not into the verdict as the run's failure.
- **`recurring` versus `churning`.** `recurring` lists issues that came back in similar words every round: the builder cannot see what the critic sees. `churning` lists critics that blocked every round, but never on the same issue twice: the critic's blocking rule is too loose. They need different fixes. Do not report churn as a hard problem.
- **`readsCode` and the conventions block are separate.** Only the critic named `consistency` gets `context`; `readsCode` only decides whether a critic may see the diff. Consistency always reads code, an extra lens like `perf` may, and craft never does, because it would grade intent instead of result.
- **The builder's `summary` never reaches a critic.** From round 2 on it describes the previous round's feedback, which is exactly the history critics must not see. Critics get `files` and `render` only.
- **No commits yet means no base.** `git rev-parse HEAD` fails in a freshly initialised repo. Pass `base: ''`, and critics read the files the builder lists.
- **Diff against `base`, not the working tree.** The builder may commit despite being told not to (a CLAUDE.md can ask for checkpoint commits), which would leave a bare `git diff` empty. A tree that was dirty before the run would mix the user's own changes in. `git diff <base> -- <files>` handles both. Record `base` in preflight.
- **Greenfield drops consistency.** With `context` empty, leave the consistency critic out of `critics` entirely. Do not pass it an empty convention list and hope it abstains.
- **Render at the output's real size.** Chrome's `--screenshot` captures full page height, not `--window-size`. Crop to the viewport or to the component's own bounds. For an interaction, capture frames across the transition, not one settled state.
- **The builder gets `render` too.** Without it, a test builder said it could not open the page and shipped a toggle it had never clicked. Checking that its own output renders is not grading it.
- **The builder works in place, without `isolation: 'worktree'`.** There is one builder and the critics need to see its work on disk.
- **No `Date.now()`, `new Date()` or `Math.random()`** in workflow scripts. They throw, because they would break resume.
- **Running out of rounds is a result.** `passed: false` comes back with `final`, `scores`, `recurring`, `churning`, `lastRoundNew`, and `declined`. Report it as unresolved. A truncated run that reports nothing reads as a run that finished.
- **Resume after a script edit**: relaunch with `{scriptPath, resumeFromRunId}`. Everything before your first edit returns from cache.
