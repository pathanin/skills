import { describe, expect, mock, test } from 'claude-code/testing'
import type { RenderPropsOf } from 'claude-code'

import {
  ALL_FRAMES,
  ANIMATIONS,
  AT_REST,
  COLORS,
  COLUMNS,
  DEFAULT,
  HEIGHT,
  PUT_AWAY,
  ROWS,
  TAKE_OUT,
  TYPING,
  WIDTH,
  cellOf,
  decode,
  encode,
  fromBase64,
  mixedCells,
  pick,
  pickTyping,
  poseGrid,
  toBase64,
} from './sprite'
import type { Grid } from '../types'

// Clawd was the Claude Code logo cell for cell (three rows of quadrant blocks). It is drawn
// now after the desktop app's Clawd, at that Clawd's proportions, in two-colour cells: the
// logo's shape (a block of a body, two eyes, arms held out, four legs) but no longer its cells.

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

type Node = { type?: string; key?: string; props?: any; children?: Node[] }

/** Clawd's leaf as drawn (its Raster's cells, or its Image), or nulls when the band is not Clawd's. */
async function drawn($: any, surface: 'terminal' | 'desktop' = 'terminal', props = {}) {
  const ui = await $.ui.mount({ ...BAND, props: { ...BAND.props, ...props }, surface })
  const found: Node | undefined = await ui.find({ key: 'clawd' })
  const beneath = await ui.findAll({ type: 'Text', text: 'beneath' })
  await ui.unmount()
  const leaf = found?.children?.[0]
  return {
    cells: leaf?.type === 'Raster' ? (leaf.props.cells as string) : null,
    image: leaf?.type === 'Image' ? leaf.props : null,
    raster: leaf?.type === 'Raster' ? { columns: leaf.props.columns, rows: leaf.props.rows } : null,
    beneath: beneath.length,
  }
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

const letters = (grid: Grid) => new Set(grid.join('').replace(/\./g, ''))
const column = (grid: Grid, x: number) => grid.map(row => row[x]).join('')

describe('cells', () => {
  test('base64 as the runtime writes it, and back', async () => {
    const bytes = Uint8Array.from({ length: 50 }, (_, i) => (i * 37) & 255)
    for (const n of [0, 1, 2, 3, 49, 50]) {
      const part = bytes.slice(0, n)
      expect(toBase64(part)).toBe((part as any).toBase64())
      expect([...fromBase64(toBase64(part))]).toEqual([...part])
    }
  })

  test('a cell takes two colours, the terminal background among them, and is never a full block', async () => {
    // Lit all over: a space on the colour, so a font's short blocks cannot stripe it.
    expect(cellOf(['o', 'o', 'o', 'o'])).toEqual({ ch: ' ', fg: DEFAULT, bg: COLORS.o! })
    // Lit in part: the glyph in the colour, on the terminal's own background.
    expect(cellOf(['o', '.', 'o', '.'])).toEqual({ ch: '▌', fg: COLORS.o!, bg: DEFAULT })
    expect(cellOf(['.', '.', 'o', 'o'])).toEqual({ ch: '▄', fg: COLORS.o!, bg: DEFAULT })
    // Two colours: the one with fewer pixels as the glyph, on the other.
    expect(cellOf(['o', 'o', 'o', 'e'])).toEqual({ ch: '▗', fg: COLORS.e!, bg: COLORS.o! })
    expect(cellOf(['o', 's', 'o', 's'])).toEqual({ ch: '▐', fg: COLORS.s!, bg: COLORS.o! })
    for (const [grid] of ALL_FRAMES) expect(decode(encode(grid)).flat().some(c => c.ch === '█')).toBe(false)
  })

  test('no cell of any frame holds three colours', async () => {
    for (const [grid] of ALL_FRAMES) expect(mixedCells(grid)).toEqual([])
  })

  test('the cells read back as encoded, one per cell', async () => {
    const cells = decode(encode(AT_REST))
    expect(cells.length).toBe(ROWS)
    for (const row of cells) expect(row.length).toBe(COLUMNS)
    // The body eight cells across, solid; its eyes; the four legs in the bottom row.
    expect(cells[3]!.filter(c => c.ch === ' ' && c.bg === COLORS.o).length).toBe(8)
    expect(cells.flat().filter(c => c.fg === COLORS.e || c.bg === COLORS.e).length).toBe(2)
    expect(cells[4]!.filter(c => c.ch === ' ' && c.bg === COLORS.o).length).toBe(4)
  })
})

describe('sprite', () => {
  test('at rest: a body with two dark eyes, an arm out from each side, four legs on the floor', async () => {
    expect(letters(AT_REST)).toEqual(new Set(['o', 'e']))
    const eyes = AT_REST.join('').split('').filter(p => p === 'e')
    expect(eyes.length).toBe(4) // two eyes, each a unit: two pixels across, one down
    expect(AT_REST[HEIGHT - 1]!.match(/o+/g)).toEqual(['oo', 'oo', 'oo', 'oo'])
    // The arms: the widest rows, reaching past the body on both sides.
    const widths = AT_REST.map(row => row.lastIndexOf('o') - row.indexOf('o'))
    expect(Math.max(...widths)).toBeGreaterThan(widths[HEIGHT - 2]! + 4)
  })

  test('the outer legs come down from the sides of the body, front and side on', async () => {
    const lit = (row: string) => [...row].flatMap((p, x) => (p === 'o' || p === 's' ? [x] : []))
    // From the front, straight down to the floor from both edges.
    const floor = lit(AT_REST[HEIGHT - 1]!)
    const body = lit(AT_REST[HEIGHT - 3]!)
    expect(floor[floor.length - 1]).toBe(body[body.length - 1])
    expect(AT_REST[HEIGHT - 3]![floor[0]!]).toBe('o')
    expect(AT_REST[HEIGHT - 3]![floor[0]! - 1]).toBe('.')
    // Side on, bent under it: the far leg starts under the far edge, in shade.
    const side = TYPING.steady![1]![0]
    const knees = lit(side[HEIGHT - 2]!)
    const back = lit(side[HEIGHT - 3]!)
    expect(knees[knees.length - 1]).toBe(back[back.length - 1])
    expect(side[HEIGHT - 2]![knees[knees.length - 1]!]).toBe('s')
  })

  test('typing is drawn side on over a laptop, a hand on the keys or not', async () => {
    const shown = Object.values(TYPING).flatMap(frames => frames.map(([g]) => g))
    for (const grid of shown) for (const p of ['g', 's']) expect(grid.join('')).toContain(p)
    // A key lit on some frames and not on others, and always under a hand.
    const lit = (g: Grid) => g[HEIGHT - 1]!.includes('w')
    expect(shown.some(lit)).toBe(true)
    expect(shown.some(g => !lit(g))).toBe(true)
    for (const g of shown.filter(lit)) expect('os').toContain(g[HEIGHT - 2]![g[HEIGHT - 1]!.indexOf('w')])
  })

  test('types with both hands in turn: the near one, and the far one in shade', async () => {
    const shown = Object.values(TYPING).flatMap(frames => frames.map(([g]) => g))
    const hand = new Set(shown.filter(g => g[HEIGHT - 1]!.includes('w')).map(g => g[HEIGHT - 2]![g[HEIGHT - 1]!.indexOf('w')]))
    expect([...hand].sort()).toEqual(['o', 's'])
  })

  test('the legs hold still while it types', async () => {
    const legs = new Set(Object.values(TYPING).flatMap(f => f.map(([g]) => g.slice(HEIGHT - 2).map(r => r.slice(28)).join('\n'))))
    expect(legs.size).toBe(1)
  })

  test('no idle animation has the laptop in it, and none is cut off at the edges', async () => {
    for (const frames of Object.values(ANIMATIONS)) {
      for (const [g] of frames) {
        for (const p of letters(g)) expect('oe').toContain(p)
        expect(column(g, 0)).toBe('.'.repeat(HEIGHT))
        expect(column(g, WIDTH - 1)).toBe('.'.repeat(HEIGHT))
      }
    }
  })

  test('every frame keeps the same size, and each animation ends at rest', async () => {
    for (const [g] of ALL_FRAMES) {
      expect(g.length).toBe(HEIGHT)
      for (const row of g) expect(row.length).toBe(WIDTH)
    }
    for (const frames of [...Object.values(ANIMATIONS), PUT_AWAY]) expect(frames[frames.length - 1]![0]).toEqual(AT_REST)
    expect(TAKE_OUT[0]![0]).toEqual(poseGrid({ look: -1 }))
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

const REST_CELLS = encode(AT_REST)

describe('while Claude works', () => {
  const TYPING_CELLS = new Set(Object.values(TYPING).flatMap(f => f.map(([g]) => encode(g))))
  const isTyping = (cells: string | null) => cells !== null && TYPING_CELLS.has(cells)
  const working = async ($: any, isWorking: boolean) => (await drawn($, 'terminal', { isWorking })).cells

  test('Clawd takes out the laptop, types the whole turn, then puts it away', async ($, on) => {
    const clock = mock.clock(on)
    beneath(on)
    await start($, on)
    expect(isTyping((await drawn($)).cells)).toBe(false)

    await working($, true)
    await clock.advance(1_500) // the laptop comes out
    const poses = new Set<string>()
    for (let t = 0; t < 30_000; t += 40) {
      await clock.advance(40)
      const cells = await working($, true)
      // Nothing but typing: no idle animation slips in.
      expect(isTyping(cells)).toBe(true)
      poses.add(cells ?? '')
    }
    expect(poses.size).toBeGreaterThan(3)

    await working($, false)
    await clock.advance(3_000) // the patch in hand, then the put-away
    expect((await drawn($)).cells).toBe(REST_CELLS)
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
  const NONE = { cells: null, image: null, raster: null, beneath: 1 }

  test('stands at the right of what the band already holds, in the terminal, in cells', async ($, on) => {
    beneath(on)
    await start($, on)
    expect(await drawn($)).toEqual({ cells: REST_CELLS, image: null, raster: { columns: COLUMNS, rows: ROWS }, beneath: 1 })
  })

  test('is not drawn on desktop: the band is left as it was', async ($, on) => {
    beneath(on)
    await start($, on)
    expect(await drawn($, 'desktop')).toEqual(NONE)
  })

  test('gives way to a survey and to a band too small for it', async ($, on) => {
    beneath(on)
    await start($, on)
    expect(await drawn($, 'terminal', { hasSurvey: true })).toEqual(NONE)
    expect(await drawn($, 'terminal', { maxRows: ROWS - 1 })).toEqual(NONE)
    expect((await drawn($, 'terminal', { maxRows: ROWS })).cells).toBe(REST_CELLS)
    expect(await drawn($, 'terminal', { bodyColumns: 30 })).toEqual(NONE)
  })

  test('/clawd hides and shows it', async ($, on) => {
    beneath(on)
    await start($, on)
    expect((await $.command.run({ command: 'clawd', args: 'hide' } as never)).text).toBe('Clawd is hiding.')
    expect(await drawn($)).toEqual(NONE)
    await $.command.run({ command: 'clawd', args: '' } as never)
    expect((await drawn($)).cells).toBe(REST_CELLS)
  })

  test('/clawd image draws it as a picture, its pixels whole, and /clawd cells back', async ($, on) => {
    beneath(on)
    await start($, on)
    await $.command.run({ command: 'clawd', args: 'image' } as never)
    const { image, cells } = await drawn($)
    expect(cells).toBe(null)
    expect(image).toEqual(expect.objectContaining({ columns: COLUMNS, rows: ROWS, alt: 'Clawd' }))
    const { width, height, rgba } = image.source
    // Whole blocks of pixels per grid pixel, in a cell's one-by-two shape.
    expect(width % WIDTH).toBe(0)
    expect(height % HEIGHT).toBe(0)
    expect(height / HEIGHT / (width / WIDTH)).toBe(2)
    const px = fromBase64(rgba)
    expect(px.length).toBe(width * height * 4)
    // The top-left pixel is clear; the middle of the body is Clawd's orange, opaque.
    expect(px[3]).toBe(0)
    const o = COLORS.o!
    const mid = 4 * (Math.floor(height * 0.65) * width + Math.floor(width * 0.6))
    expect([...px.slice(mid, mid + 4)]).toEqual([(o >> 16) & 255, (o >> 8) & 255, o & 255, 255])
    await $.command.run({ command: 'clawd', args: 'cells' } as never)
    expect((await drawn($)).cells).toBe(REST_CELLS)
  })

  test('plays a different pose within ten seconds, then comes back to rest', async ($, on) => {
    const clock = mock.clock(on)
    beneath(on)
    await start($, on)
    const poses = new Set<string>()
    for (let t = 0; t < 10_000; t += 50) {
      await clock.advance(50)
      poses.add((await drawn($)).cells ?? '')
    }
    expect(poses.size).toBeGreaterThan(1)
    await clock.advance(5_000)
    // Somewhere in a rest of at least three seconds once the animation is over.
    let atRest = false
    for (let t = 0; t < 15_000 && !atRest; t += 50) {
      await clock.advance(50)
      atRest = (await drawn($)).cells === REST_CELLS
    }
    expect(atRest).toBe(true)
  })
})

describe('beside the other rows', () => {
  const row = (plugin: string, text: string) => ({ plugin, tree: h('Text', null, text) })
  const LIST = {
    plugin: 'clawd',
    component: 'AbovePromptList',
    props: { ...BAND.props, isCollapsed: false, rows: [row('live-tasks', 'tasks'), row('clawd', 'clawd')] },
  } as const

  async function listed($: any, props = {}) {
    const ui = await $.ui.mount({ ...LIST, props: { ...LIST.props, ...props }, surface: 'terminal' })
    const beside = await ui.find({ key: 'clawd-beside' })
    const texts = (await ui.findAll({ type: 'Text' })).map((t: Node & { text?: string }) => t.text)
    await ui.unmount()
    return { isBeside: beside !== undefined, texts }
  }

  test('shares the task list rows instead of stacking under them', async ($, on) => {
    await start($, on)
    expect(await listed($)).toEqual({ isBeside: true, texts: ['tasks', 'clawd'] })
  })

  test('steps out when the rows beside it would be cut short', async ($, on) => {
    await start($, on)
    expect(await listed($, { bodyColumns: COLUMNS + 47 })).toEqual({ isBeside: false, texts: ['tasks'] })
    expect((await listed($, { bodyColumns: COLUMNS + 48 })).isBeside).toBe(true)
  })

  test('alone in the band, its row is left as the engine stacks it', async ($, on) => {
    await start($, on)
    expect(await listed($, { rows: [row('clawd', 'clawd')] })).toEqual({ isBeside: false, texts: ['clawd'] })
  })
})
