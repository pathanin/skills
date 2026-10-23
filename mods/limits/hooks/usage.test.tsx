import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

const BAND = {
  plugin: 'limits',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isWorking: false,
    maxRows: 20,
    bodyColumns: 120,
    scroll: { offset: 0, bodyRows: 20 },
    view: {},
  },
} as const

/** Upstream's behaviour: the band in the terminal too. */
const EVERYWHERE = { options: { show: 'everywhere' } }

const inHours = (h: number) => new Date(Date.now() + h * 3_600_000).toISOString()

type Window = { utilization: number; resets_at: string }

/** A claude.ai login, and Anthropic's usage endpoint answering `body()`; counts the asks. */
const usageApi = (on: On, body: () => Record<string, Window>) => {
  const asks = { n: 0 }
  on('session.authorize', () => ({ value: { handle: 'h', kind: 'bearer' } }) as never)
  on('http.fetch', () => {
    asks.n += 1
    return { value: { status: 200, ok: true, headers: {}, text: JSON.stringify(body()) } } as never
  })
  on('session.usage', () => ({ value: { startedAt: 0, context: { window: 200_000 }, rateLimits: [] } }) as never)
  return asks
}

test('one compact line: limit, bar, percent, reset or run-out', EVERYWHERE, async ($, on) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  mock.store(on)
  on('session.measure', ($, e) => ({ changed: e.changed }))
  on('ui.status', () => ({ value: undefined }) as never)
  on('ui.toast', () => ({ value: undefined }) as never)
  await $.session.measure({
    context: { tokens: 84_200, window: 200_000, percent: 42 },
    rateLimits: [
      { kind: 'seven_day', percentUsed: 61, resetsAt: inHours(72) },
      { kind: 'five_hour', percentUsed: 23.5, resetsAt: inHours(2) },
    ],
    cost: { usd: 1.234 },
    changed: ['context', 'rateLimits', 'cost'],
  })

  await $.session.measure({
    context: { window: 200_000 },
    rateLimits: [
      { kind: 'seven_day', percentUsed: 62.5, resetsAt: inHours(72) },
      { kind: 'five_hour', percentUsed: 27, resetsAt: inHours(2) },
    ],
    changed: ['rateLimits'],
  })

  const term = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await term.find({ type: 'Text', text: 'context ' })).toBeDefined()
  expect(await term.find({ type: 'Text', text: '84.2k/200k' })).toBeDefined()
  for (const text of ['5hr', 'week', '27%', '63%', /2h/, /[23]d/]) {
    expect(await term.find({ type: 'Text', text })).toBeDefined()
  }
  expect(await term.find({ type: 'Text', text: /out / })).toBeUndefined()
  const weekly = (await term.findAll({ type: 'Text', text: ' 63%' }))[0] as unknown as { props: { color?: string } }
  expect(weekly.props.color).toBe('error')
  for (const text of [/COST|session|budget/]) {
    expect(await term.find({ type: 'Text', text })).toBeUndefined()
  }
  await term.unmount()

  const desk = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect(await desk.findAll({ type: 'Svg' })).toHaveLength(1)
  await desk.unmount()
})

test('band waits politely before any reading', EVERYWHERE, async ($, on) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  mock.store(on)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /after the first reply/ })).toBeDefined()
  await ui.unmount()
})

test('refresh button asks Anthropic once, takes its figures, and never pins a status line', EVERYWHERE, async ($, on) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  mock.store(on)
  mock.clock(on, { now: Date.now() })
  const statuses: (string | undefined)[] = []
  const resets = inHours(3)
  on('session.measure', ($, e) => ({ changed: e.changed }))
  on('ui.status', ($, e) => {
    statuses.push(e.text)
    return { value: undefined } as never
  })
  on('ui.toast', () => ({ value: undefined }) as never)
  const asks = usageApi(on, () => ({ five_hour: { utilization: 92, resets_at: resets } }))

  await $.session.measure({ context: { window: 200_000 }, rateLimits: [{ kind: 'five_hour', percentUsed: 20, resetsAt: resets }], changed: ['rateLimits'] })

  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await ui.find({ key: 'refresh' })).toBeDefined()
  await ui.press({ key: 'refresh' })
  await ui.press({ key: 'refresh' })
  expect(asks.n).toBe(1)
  await ui.unmount()
  const after = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await after.find({ type: 'Text', text: ' 92%' })).toBeDefined()
  expect(statuses.filter(t => t !== undefined)).toHaveLength(0)
  await after.unmount()
})

test('a stale reply figure lasts one slot at most: then the bar shows the real one', EVERYWHERE, async ($, on) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  mock.store(on)
  const clock = mock.clock(on, { now: Date.now() })
  const week = inHours(100)
  on('session.start', async (_$, e) => ({ cwd: e.cwd }))
  on('session.measure', ($, e) => ({ changed: e.changed }))
  on('ui.toast', () => ({ value: undefined }) as never)
  on('ui.status', () => ({ value: undefined }) as never)
  usageApi(on, () => ({ seven_day: { utilization: 38, resets_at: week } }))
  await $.session.start({ cwd: '/tmp', surface: 'desktop', isInteractive: true })
  // An idle chat replays what it saw earlier this week.
  await $.session.measure({ context: { window: 200_000 }, rateLimits: [{ kind: 'seven_day', percentUsed: 36, resetsAt: week }], changed: ['rateLimits'] })
  await clock.advance(2 * 60_000)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: ' 38%' })).toBeDefined()
  await ui.unmount()
})

test('with an API key there is nothing to ask: no request, replies still fill the bar', EVERYWHERE, async ($, on) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  mock.store(on)
  const clock = mock.clock(on, { now: Date.now() })
  let fetches = 0
  let pings = 0
  on('session.start', async (_$, e) => ({ cwd: e.cwd }))
  on('session.measure', ($, e) => ({ changed: e.changed }))
  on('ui.toast', () => ({ value: undefined }) as never)
  on('session.authorize', () => ({ value: { handle: 'k', kind: 'api-key' } }) as never)
  on('http.fetch', () => {
    fetches += 1
    return { value: { status: 200, ok: true, headers: {}, text: '{}' } } as never
  })
  on('model.complete', () => {
    pings += 1
    return { value: { isAnswered: true, text: '.' } } as never
  })
  on('session.usage', () => ({ value: { startedAt: 0, context: { window: 200_000 }, rateLimits: [] } }) as never)
  await $.session.start({ cwd: '/tmp', surface: 'desktop', isInteractive: true })
  await clock.advance(6 * 60_000)
  expect(fetches).toBe(0)
  expect(pings).toBe(0)
  await $.session.measure({ context: { window: 200_000 }, rateLimits: [{ kind: 'five_hour', percentUsed: 40, resetsAt: inHours(2) }], changed: ['rateLimits'] })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: ' 40%' })).toBeDefined()
  await ui.unmount()
})

test('a reading that names only one window keeps the other on the bar', EVERYWHERE, async ($, on) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  mock.store(on)
  on('session.measure', ($, e) => ({ changed: e.changed }))
  on('ui.toast', () => ({ value: undefined }) as never)
  await $.session.measure({
    context: { window: 200_000 },
    rateLimits: [
      { kind: 'five_hour', percentUsed: 20, resetsAt: inHours(3) },
      { kind: 'seven_day', percentUsed: 80, resetsAt: inHours(30) },
    ],
    changed: ['rateLimits'],
  })
  await $.session.measure({
    context: { window: 200_000 },
    rateLimits: [{ kind: 'seven_day', percentUsed: 81, resetsAt: inHours(30) }],
    changed: ['rateLimits'],
  })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: '5hr ' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: ' 81%' })).toBeDefined()
  await ui.unmount()
})

test('auto refresh asks once per 30-second slot', EVERYWHERE, async ($, on) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  mock.store(on)
  const clock = mock.clock(on, { now: Date.now() })
  on('session.start', async (_$, e) => ({ cwd: e.cwd }))
  on('session.measure', ($, e) => ({ changed: e.changed }))
  on('ui.toast', () => ({ value: undefined }) as never)
  on('ui.status', () => ({ value: undefined }) as never)
  const asks = usageApi(on, () => ({ five_hour: { utilization: 20, resets_at: inHours(3) } }))
  await $.session.start({ cwd: '/tmp', surface: 'desktop', isInteractive: true })
  await clock.advance(10 * 60_000)
  // Ten minutes is twenty slots, plus the one the start falls in.
  expect(asks.n).toBeGreaterThanOrEqual(20)
  expect(asks.n).toBeLessThanOrEqual(21)
})

test('a chat that never saw session.start still pulls the shared reading and shows both limits', EVERYWHERE, async ($, on) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  const at = Date.now()
  mock.store(on, {
    latest: {
      limits: [
        { kind: 'five_hour', percentUsed: 9, resetsAt: inHours(4) },
        { kind: 'seven_day', percentUsed: 83, resetsAt: inHours(30) },
      ],
      at,
    },
    lastSlot: Math.floor(at / 120_000),
  })
  const clock = mock.clock(on, { now: at })
  on('ui.toast', () => ({ value: undefined }) as never)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  await clock.advance(1_000)
  await ui.unmount()
  const again = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await again.find({ type: 'Text', text: '5hr ' })).toBeDefined()
  expect(await again.find({ type: 'Text', text: ' 83%' })).toBeDefined()
  await again.unmount()
})

test('a stale figure handed over later never pulls a window back down', EVERYWHERE, async ($, on) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  mock.store(on)
  on('session.measure', ($, e) => ({ changed: e.changed }))
  on('ui.toast', () => ({ value: undefined }) as never)
  const week = inHours(9)
  await $.session.measure({ context: { window: 200_000 }, rateLimits: [{ kind: 'seven_day', percentUsed: 94, resetsAt: week }], changed: ['rateLimits'] })
  // An idle chat reports what it last saw, hours ago, for the same week.
  await $.session.measure({ context: { window: 200_000 }, rateLimits: [{ kind: 'seven_day', percentUsed: 87, resetsAt: week }], changed: ['rateLimits'] })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: ' 94%' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: ' 87%' })).toBeUndefined()
  await ui.unmount()
  // A new week starts lower, and that does replace it.
  await $.session.measure({ context: { window: 200_000 }, rateLimits: [{ kind: 'seven_day', percentUsed: 3, resetsAt: inHours(9 + 168) }], changed: ['rateLimits'] })
  const after = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await after.find({ type: 'Text', text: ' 3%' })).toBeDefined()
  await after.unmount()
})

test('a live reading lower than the stored one replaces it (plan upgrade mid-week)', EVERYWHERE, async ($, on) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  const week = inHours(147)
  const at = Date.now()
  mock.store(on, { latest: { limits: [{ kind: 'seven_day', percentUsed: 26, resetsAt: week }], at } })
  mock.clock(on, { now: at + 60_000 })
  on('session.measure', ($, e) => ({ changed: e.changed }))
  on('ui.status', () => ({ value: undefined }) as never)
  on('ui.toast', () => ({ value: undefined }) as never)
  usageApi(on, () => ({ seven_day: { utilization: 10, resets_at: week } }))

  await $.session.measure({ context: { window: 200_000 }, rateLimits: [{ kind: 'seven_day', percentUsed: 26, resetsAt: week }], changed: ['rateLimits'] })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: ' 26%' })).toBeDefined()
  await ui.press({ key: 'refresh' })
  await ui.unmount()
  const after = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await after.find({ type: 'Text', text: ' 10%' })).toBeDefined()
  expect(await after.find({ type: 'Text', text: ' 26%' })).toBeUndefined()
  await after.unmount()

  // An idle chat replaying its pre-upgrade figure does not bring it back.
  await $.session.measure({ context: { window: 200_000 }, rateLimits: [{ kind: 'seven_day', percentUsed: 26, resetsAt: week }], changed: ['rateLimits'] })
  const replay = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await replay.find({ type: 'Text', text: ' 10%' })).toBeDefined()
  await replay.unmount()
})

test("another mod's band beneath draws under the bars", EVERYWHERE, async ($, on) => {
  mock.store(on)
  on('ui.render', () => ({ type: 'Text', props: {}, children: ['quick replies'] }) as never)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /after the first reply/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: 'quick replies' })).toBeDefined()
  await ui.unmount()
})

/** A session started by `entrypoint` (the desktop app sets `claude-desktop`). */
const startedBy = (on: On, entrypoint: string | undefined) =>
  on('env.get', ($, e) => ({ value: e.name === 'CLAUDE_CODE_ENTRYPOINT' ? entrypoint : undefined }) as never)

test('app only: a terminal session draws nothing, asks nothing and raises no toast', async ($, on) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  mock.store(on)
  const clock = mock.clock(on, { now: Date.now() })
  startedBy(on, 'cli')
  const toasts: string[] = []
  on('session.start', async (_$, e) => ({ cwd: e.cwd }))
  on('session.measure', ($, e) => ({ changed: e.changed }))
  on('ui.toast', ($, e) => {
    toasts.push(e.text)
    return { value: undefined } as never
  })
  const asks = usageApi(on, () => ({ five_hour: { utilization: 95, resets_at: inHours(2) } }))

  await $.session.start({ cwd: '/tmp', surface: 'terminal', isInteractive: true })
  await $.session.measure({ context: { window: 200_000 }, rateLimits: [{ kind: 'five_hour', percentUsed: 95, resetsAt: inHours(2) }], changed: ['rateLimits'] })
  await clock.advance(5 * 60_000)

  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await ui.find({ type: 'Text' })).toBeUndefined()
  expect(await ui.find({ key: 'refresh' })).toBeUndefined()
  await ui.unmount()
  expect(asks.n).toBe(0)
  expect(toasts).toHaveLength(0)
})

test('app only: the desktop app draws the band; a terminal attached to it does not', async ($, on) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  mock.store(on)
  startedBy(on, 'claude-desktop')
  on('session.measure', ($, e) => ({ changed: e.changed }))
  on('ui.toast', () => ({ value: undefined }) as never)
  await $.session.measure({ context: { window: 200_000 }, rateLimits: [{ kind: 'five_hour', percentUsed: 30, resetsAt: inHours(2) }], changed: ['rateLimits'] })

  const desk = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect(await desk.findAll({ type: 'Svg' })).toHaveLength(1)
  expect(await desk.find({ key: 'refresh' })).toBeDefined()
  await desk.unmount()

  const term = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await term.find({ type: 'Text' })).toBeUndefined()
  await term.unmount()
})

test('low usage early in a window stays green even on a run-out pace', EVERYWHERE, async ($, on) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  mock.store(on)
  on('session.measure', ($, e) => ({ changed: e.changed }))
  on('ui.status', () => ({ value: undefined }) as never)
  on('ui.toast', () => ({ value: undefined }) as never)
  // 6% used 14 minutes in: the rate projects past 100% before the reset, but 6% is not a warning.
  await $.session.measure({
    context: { window: 200_000 },
    rateLimits: [{ kind: 'five_hour', percentUsed: 6, resetsAt: inHours(4 + 46 / 60) }],
    changed: ['rateLimits'],
  })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  const pct = (await ui.findAll({ type: 'Text', text: ' 6%' }))[0] as unknown as { props: { color?: string } }
  expect(pct.props.color).toBe('success')
  await ui.unmount()
})

/** The screenshot's figures: 5hr 8%, week 17%, context 14% of 1M. */
const screenshotBand = async (
  $: Parameters<Parameters<typeof test>[2]>[0],
  on: On,
  surface: 'desktop' | 'terminal',
  bodyColumns: number,
  /** Near the widest figures the band shows: two-digit percents, `6d23h`, `999.9k/1M`. */
  isLong = false,
) => {
  on('ui.render', () => ({ type: 'engine', ref: 0 }))
  mock.store(on)
  on('session.measure', ($, e) => ({ changed: e.changed }))
  on('ui.status', () => ({ value: undefined }) as never)
  on('ui.toast', () => ({ value: undefined }) as never)
  await $.session.measure({
    context: isLong
      ? { tokens: 999_900, window: 1_000_000, percent: 99 }
      : { tokens: 140_400, window: 1_000_000, percent: 14 },
    rateLimits: [
      { kind: 'five_hour', percentUsed: isLong ? 88 : 8, resetsAt: inHours(4 + 41 / 60) },
      { kind: 'seven_day', percentUsed: isLong ? 88 : 17, resetsAt: inHours(isLong ? 6 * 24 + 23.5 : 3 * 24 + 21) },
    ],
    changed: ['context', 'rateLimits'],
  })
  return $.ui.mount({ ...BAND, surface, props: { ...BAND.props, bodyColumns } })
}

const svgOf = async (ui: Awaited<ReturnType<typeof screenshotBand>>) =>
  ((await ui.findAll({ type: 'Svg' }))[0] as unknown as { props: { source: string; alt: string } }).props

test('a narrow desktop band shows the 5-hour limit alone, and every limit in its alt text', EVERYWHERE, async ($, on) => {
  const ui = await screenshotBand($, on, 'desktop', 62)
  const { source, alt } = await svgOf(ui)
  expect(source).toContain('5hr')
  expect(source).not.toContain('week')
  expect(source).not.toContain('context')
  expect(alt).toContain('Weekly')
  expect(await ui.find({ key: 'refresh' })).toBeDefined()
  await ui.unmount()
})

test('the desktop band at full window width (85 cells) shows every limit, even with long figures', EVERYWHERE, async ($, on) => {
  const ui = await screenshotBand($, on, 'desktop', 85, true)
  const { source } = await svgOf(ui)
  for (const label of ['5hr', 'week', 'context']) expect(source).toContain(label)
  await ui.unmount()
})

test('a narrow terminal band shows the 5-hour limit alone', EVERYWHERE, async ($, on) => {
  const ui = await screenshotBand($, on, 'terminal', 40)
  expect(await ui.find({ type: 'Text', text: '5hr ' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: 'week ' })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: 'context ' })).toBeUndefined()
  await ui.unmount()
})
