import { describe, expect, mock, test } from 'claude-code/testing'
import type { RenderPropsOf } from 'claude-code'

import { ANIMATIONS, draw, pick } from './sprite'

const REST = ['  ▐▛███▜▌  ', ' ▝▜█████▛▘ ', '   ▘▘ ▝▝   ']

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
  test('at rest it is the Claude Code logo, one empty column either side', async () => {
    expect([...draw()]).toEqual(REST)
  })

  test('every frame of every animation keeps the same size, so the band never jumps', async () => {
    for (const frames of Object.values(ANIMATIONS)) {
      for (const [pose] of frames) {
        const rows = draw(pose)
        expect(rows.length).toBe(3)
        for (const row of rows) expect(row.length).toBe(11)
      }
      expect([...draw(frames[frames.length - 1]![0])]).toEqual(REST)
    }
  })

  test('picks every animation over the range, never the one just played', async () => {
    const seen = new Set<string>()
    for (let i = 0; i < 1000; i++) seen.add(pick(i / 1000, null))
    expect([...seen].sort()).toEqual(Object.keys(ANIMATIONS).sort())
    for (let i = 0; i < 1000; i++) expect(pick(i / 1000, 'blink')).not.toBe('blink')
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
