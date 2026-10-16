import { describe, expect, mock, test } from 'claude-code/testing'
import type { RenderPropsOf } from 'claude-code'

import { ANIMATIONS, LAPTOP_GRIDS, PUT_AWAY, TAKE_OUT, TYPING, draw, mixedCells, pick, pickTyping, plain } from './sprite'

const REST = ['     ▐▛███▜▌  ', '    ▝▜█████▛▘ ', '      ▘▘ ▝▝   ']

const BAND = {
  plugin: 'clawd',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isWorking: false,
    maxRows: 20,
    bodyColumns: 80,
    scroll: { bodyRows: 19, offset: 0 },
  } as unknown as RenderPropsOf['AbovePrompt'],
} as const

type Node = { type?: string; key?: string; props?: { key?: string }; children?: unknown[] } | string

function text(node: Node): string {
  if (typeof node === 'string') return node
  return (node.children ?? []).map(c => text(c as Node)).join('')
}

/** Clawd's rows as drawn, or null when the band is not Clawd's. */
async function drawn($: any, surface: 'terminal' | 'desktop' = 'terminal', props = {}) {
  const ui = await $.ui.mount({ ...BAND, props: { ...BAND.props, ...props }, surface })
  const found = await ui.find({ key: 'clawd' })
  const beneath = await ui.findAll({ type: 'Text', text: 'beneath' })
  await ui.unmount()
  return { rows: found === undefined ? null : ((found.children ?? []) as Node[]).map(text), beneath: beneath.length }
}

// Stands for what sits beneath Clawd in the band: the engine, or another mod's list.
const beneath = (on: any) =>
  on('ui.render', { component: 'AbovePrompt' }, ($: any, e: any) => {
    const { Text } = $.ui.resolve(e)
    return h(Text, null, 'beneath')
  })

async function start($: any, on: any) {
  on('session.surfaces', () => ({ value: ['terminal'] }))
  on('command.register', () => ({ value: { command: 'clawd' } }))
  on('session.start', () => ({ cwd: '/' }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
}

describe('sprite', () => {
  test('at rest it is the Claude Code logo, with room around it', async () => {
    expect(plain(draw())).toEqual(REST)
  })

  test('at the laptop, no cell mixes two colours', async () => {
    for (const grid of LAPTOP_GRIDS) expect(mixedCells(grid)).toEqual([])
  })

  test('typing is drawn side on over a laptop open on the floor, the hand going up and down', async () => {
    const shown = Object.values(TYPING).flatMap(frames => frames.map(([s]) => s))
    for (const sprite of shown) {
      const laptop = sprite.map(row => row.filter(r => r.tone === 'laptop').map(r => r.text.trim()).join(''))
      expect(laptop).toEqual(['', '▚', expect.stringMatching(/^▙▄▄?$/)])
      expect(sprite[0]!.some(r => r.tone === 'shade')).toBe(true)
    }
    // The hand: above the keys on one frame, on them (a key lit) on the next.
    const lit = (s: (typeof shown)[number]) => s[2]!.some(r => r.tone === 'key')
    expect(shown.some(lit)).toBe(true)
    expect(shown.some(s => !lit(s))).toBe(true)
  })

  test('no idle animation has the laptop in it', async () => {
    for (const frames of Object.values(ANIMATIONS)) {
      for (const [s] of frames) expect(s.flat().some(r => r.tone !== 'clawd')).toBe(false)
    }
  })

  test('every frame keeps the same size, so the band never jumps', async () => {
    for (const frames of [...Object.values(ANIMATIONS), ...Object.values(TYPING), TAKE_OUT, PUT_AWAY]) {
      for (const [s] of frames) {
        const rows = plain(s)
        expect(rows.length).toBe(3)
        for (const row of rows) expect(row.length).toBe(14)
      }
    }
    for (const frames of [...Object.values(ANIMATIONS), PUT_AWAY]) expect(plain(frames[frames.length - 1]![0])).toEqual(REST)
  })

  test('picks every animation over the range, never the one just played', async () => {
    const seen = new Set<string>()
    for (let i = 0; i < 1000; i++) seen.add(pick(i / 1000, null))
    expect([...seen].sort()).toEqual(Object.keys(ANIMATIONS).sort())
    for (let i = 0; i < 1000; i++) expect(pick(i / 1000, 'blink')).not.toBe('blink')
    const typing = new Set<string>()
    for (let i = 0; i < 1000; i++) typing.add(pickTyping(i / 1000))
    expect([...typing].sort()).toEqual(Object.keys(TYPING).sort())
  })
})

describe('while Claude works', () => {
  // The laptop on the floor, and Clawd crouched at it: the drawings of the typing alone.
  const TYPING_ROWS = new Set(Object.values(TYPING).flatMap(f => f.map(([s]) => plain(s).join('\n'))))
  const isTyping = (rows: string[] | null) => TYPING_ROWS.has((rows ?? []).join('\n'))
  const working = async ($: any, isWorking: boolean) => (await drawn($, 'terminal', { isWorking })).rows

  test('Clawd takes out the laptop, types the whole turn, then puts it away', async ($, on) => {
    const clock = mock.clock(on)
    beneath(on)
    await start($, on)
    expect(isTyping((await drawn($)).rows)).toBe(false)

    await working($, true)
    await clock.advance(1_500) // the laptop comes out
    const poses = new Set<string>()
    for (let t = 0; t < 30_000; t += 40) {
      await clock.advance(40)
      const rows = await working($, true)
      // Nothing but typing: no idle animation slips in.
      expect(isTyping(rows)).toBe(true)
      poses.add((rows ?? []).join('\n'))
    }
    expect(poses.size).toBeGreaterThan(3)

    await working($, false)
    await clock.advance(3_000) // the patch in hand, then the put-away
    expect((await drawn($)).rows).toEqual(REST)
  })

  test("a moment's pause in the turn does not put the laptop away", async ($, on) => {
    const clock = mock.clock(on)
    beneath(on)
    await start($, on)
    await working($, true)
    await clock.advance(1_500)
    // A 30ms pause once a second, landing at every point of the typing over the run.
    for (let blip = 0; blip < 30; blip++) {
      await working($, false)
      await clock.advance(30)
      for (let t = 0; t < 970; t += 97) {
        expect(isTyping(await working($, true))).toBe(true)
        await clock.advance(97)
      }
    }
  })
})

describe('band', () => {
  test('stands at the right of what the band already holds, in the terminal', async ($, on) => {
    beneath(on)
    await start($, on)
    expect(await drawn($)).toEqual({ rows: REST, beneath: 1 })
  })

  test('is not drawn on desktop: the band is left as it was', async ($, on) => {
    beneath(on)
    await start($, on)
    expect(await drawn($, 'desktop')).toEqual({ rows: null, beneath: 1 })
  })

  test('gives way to a survey and to a band too small for it', async ($, on) => {
    beneath(on)
    await start($, on)
    expect(await drawn($, 'terminal', { hasSurvey: true })).toEqual({ rows: null, beneath: 1 })
    expect(await drawn($, 'terminal', { maxRows: 2 })).toEqual({ rows: null, beneath: 1 })
    expect(await drawn($, 'terminal', { bodyColumns: 30 })).toEqual({ rows: null, beneath: 1 })
  })

  test('/clawd hides and shows it', async ($, on) => {
    beneath(on)
    await start($, on)
    expect((await $.command.run({ command: 'clawd', args: 'hide' } as never)).text).toBe('Clawd is hiding.')
    expect(await drawn($)).toEqual({ rows: null, beneath: 1 })
    await $.command.run({ command: 'clawd', args: '' } as never)
    expect((await drawn($)).rows).toEqual(REST)
  })

  test('plays a different pose within ten seconds, then comes back to rest', async ($, on) => {
    const clock = mock.clock(on)
    beneath(on)
    await start($, on)
    const poses = new Set<string>()
    for (let t = 0; t < 10_000; t += 50) {
      await clock.advance(50)
      poses.add(((await drawn($)).rows ?? []).join('\n'))
    }
    expect(poses.size).toBeGreaterThan(1)
    await clock.advance(5_000)
    // Somewhere in a rest of at least three seconds once the animation is over.
    let atRest = false
    for (let t = 0; t < 15_000 && !atRest; t += 50) {
      await clock.advance(50)
      atRest = ((await drawn($)).rows ?? []).join('\n') === REST.join('\n')
    }
    expect(atRest).toBe(true)
  })
})
