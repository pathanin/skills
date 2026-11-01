import type { Grid } from '../types'

// Clawd is drawn on a grid of pixels, two across and two down per terminal cell, and painted
// into a `Raster`: each cell a quadrant glyph with a foreground and a background colour, so a
// cell can hold two colours, or one colour and the terminal's own background. That is what
// lets the eyes be dark, the far side be in shade and the laptop sit up against Clawd, and
// what lets a move of one pixel stay crisp.
//
// It is the desktop app's Clawd at that Clawd's own proportions (see Units below), with room
// either side to shuffle and, on its left, for the laptop. While Claude works it does what
// the desktop app's Clawd does: turns, takes out a laptop, sets it open on the floor and
// crouches over it, side on, tapping the keys.

export const WIDTH = 52 // pixels: 26 cells
export const HEIGHT = 10 // pixels: 5 rows
export const COLUMNS = WIDTH / 2
export const ROWS = HEIGHT / 2

// A grid is HEIGHT strings of WIDTH pixels: '.' empty, 'o' Clawd, 's' Clawd in shade, 'e' an
// eye, 'g' the laptop, 'w' a key lit as it is pressed.
export const COLORS: Record<string, number> = {
  o: 0xd77757, // the 'claude' orange of the CLI's theme
  s: 0xa8563c,
  e: 0x2a1a14,
  g: 0x8a8a8a,
  w: 0xf2f2f2,
}

/** The terminal's own colour: bit 24 alone. */
export const DEFAULT = 0x01000000

// Bits of a cell: top-left, top-right, bottom-left, bottom-right.
export const QUADRANT = [' ', '▘', '▝', '▀', '▖', '▌', '▞', '▛', '▗', '▚', '▐', '▜', '▄', '▙', '▟', '█']

/** One cell as painted: a glyph, its colour and the colour behind it. */
export type Cell = { ch: string; fg: number; bg: number }

const at = (grid: Grid, x: number, y: number) => grid[y]?.[x] ?? '.'
const pixelsOf = (grid: Grid, c: number, r: number) => [
  at(grid, 2 * c, 2 * r),
  at(grid, 2 * c + 1, 2 * r),
  at(grid, 2 * c, 2 * r + 1),
  at(grid, 2 * c + 1, 2 * r + 1),
]

/**
 * A cell's four pixels as one glyph in two colours. Empty pixels take the terminal's
 * background; a cell lit all over is a space on a coloured background, never a `█`, since a
 * font's blocks can fall short of the row (macOS Terminal) and stripe Clawd. Of two colours
 * the one with more pixels is the background. A third colour, which no frame should hold
 * (see `mixedCells`), is drawn as the background.
 */
export function cellOf(pixels: readonly string[]): Cell {
  const counts = new Map<string, number>()
  for (const p of pixels) counts.set(p, (counts.get(p) ?? 0) + 1)
  const colour = (p: string) => (p === '.' ? DEFAULT : (COLORS[p] ?? COLORS.o!))
  // Empty is always behind; otherwise the majority, the top-left pixel's on a tie.
  const ranked = [...counts.keys()].sort((a, b) => {
    if (a === '.' || b === '.') return a === '.' ? -1 : 1
    return (counts.get(b) ?? 0) - (counts.get(a) ?? 0) || pixels.indexOf(a) - pixels.indexOf(b)
  })
  const back = ranked[0]!
  const front = ranked[1]
  if (front === undefined) return { ch: ' ', fg: DEFAULT, bg: colour(back) }
  const bits = pixels.reduce((sum, p, i) => (p === front ? sum | (1 << i) : sum), 0)
  return { ch: QUADRANT[bits]!, fg: colour(front), bg: colour(back) }
}

export function cellsOf(grid: Grid): Cell[][] {
  return Array.from({ length: ROWS }, (_, r) => Array.from({ length: COLUMNS }, (_, c) => cellOf(pixelsOf(grid, c, r))))
}

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

/** Standard padded base64, as `Uint8Array.prototype.toBase64` gives (not in the es2023 types). */
export function toBase64(bytes: Uint8Array): string {
  let out = ''
  for (let i = 0; i < bytes.length; i += 3) {
    const [a, b, c] = [bytes[i]!, bytes[i + 1], bytes[i + 2]]
    const n = (a << 16) | ((b ?? 0) << 8) | (c ?? 0)
    out += B64[(n >> 18) & 63]! + B64[(n >> 12) & 63]!
    out += b === undefined ? '=' : B64[(n >> 6) & 63]!
    out += c === undefined ? '=' : B64[n & 63]!
  }
  return out
}

export function fromBase64(text: string): Uint8Array {
  const clean = text.replace(/=+$/, '')
  const out = new Uint8Array(Math.floor((clean.length * 3) / 4))
  let bits = 0
  let acc = 0
  let j = 0
  for (const ch of clean) {
    acc = (acc << 6) | B64.indexOf(ch)
    bits += 6
    if (bits >= 8) {
      bits -= 8
      out[j++] = (acc >> bits) & 255
    }
  }
  return out
}

const encoded = new Map<string, string>()

/** A grid as a `Raster`'s `cells`: row-major `[codePoint, foreground, background]` u32s, base64. */
export function encode(grid: Grid): string {
  const key = grid.join('\n')
  const hit = encoded.get(key)
  if (hit !== undefined) return hit
  const words = new Uint32Array(COLUMNS * ROWS * 3)
  cellsOf(grid)
    .flat()
    .forEach((cell, i) => words.set([cell.ch.codePointAt(0)!, cell.fg, cell.bg], 3 * i))
  const out = toBase64(new Uint8Array(words.buffer))
  encoded.set(key, out)
  return out
}

/** `encode` read back: what a Raster's cells say, row by row. */
export function decode(cells: string): Cell[][] {
  const bytes = fromBase64(cells)
  const words = new Uint32Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 4)
  return Array.from({ length: ROWS }, (_, r) =>
    Array.from({ length: COLUMNS }, (_, c) => {
      const i = 3 * (r * COLUMNS + c)
      return { ch: String.fromCodePoint(words[i]!), fg: words[i + 1]!, bg: words[i + 2]! }
    }),
  )
}

/** A grid as RGBA pixels, each grid pixel `sx` by `sy` of them, empty ones clear: an Image's. */
export function rgba(grid: Grid, sx: number, sy: number): Uint8Array {
  const out = new Uint8Array(WIDTH * sx * HEIGHT * sy * 4)
  for (let y = 0; y < HEIGHT * sy; y++) {
    for (let x = 0; x < WIDTH * sx; x++) {
      const p = at(grid, Math.floor(x / sx), Math.floor(y / sy))
      if (p === '.') continue
      const c = COLORS[p] ?? COLORS.o!
      out.set([(c >> 16) & 255, (c >> 8) & 255, c & 255, 255], 4 * (y * WIDTH * sx + x))
    }
  }
  return out
}

/** Cells whose pixels hold three or more colours, empty among them: what a cell cannot draw. */
export function mixedCells(grid: Grid): string[] {
  const mixed: string[] = []
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLUMNS; c++) if (new Set(pixelsOf(grid, c, r)).size > 2) mixed.push(`row ${r} cell ${c}`)
  }
  return mixed
}

/** `top`'s pixels laid over `base`'s. */
function overlay(base: Grid, top: Grid): Grid {
  return base.map((row, y) =>
    [...row]
      .map((p, x) => {
        const over = top[y]?.[x] ?? '.'
        return over === '.' ? p : over
      })
      .join(''),
  )
}

function canvas() {
  const on = Array.from({ length: HEIGHT }, () => new Array<string>(WIDTH).fill('.'))
  const set = (x: number, y: number, p = 'o') => {
    const row = on[y]
    if (row !== undefined && x >= 0 && x < WIDTH) row[x] = p
  }
  const fill = (x0: number, y0: number, x1: number, y1: number, p = 'o') => {
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) set(x, y, p)
  }
  return { on, set, fill, grid: (): Grid => on.map(row => row.join('')) }
}

// ─── Units ─────────────────────────────────────────────────────────────────────────────────
//
// Clawd is drawn after the desktop app's, square pixel for square pixel. A cell is about
// twice as tall as it is wide, so one of the desktop's square pixels is a cell across and
// half a row down: two of the grid's pixels side by side. Drawn in those units, at rest:
//
//      ..########..
//      ..#e####e#..
//      ############
//      ############
//      ..########..
//      ..#.#..#.#..
//      ..#.#..#.#..
//
// The desktop's body is a unit taller; a half-row is a little taller than a cell is wide,
// and at six it reads too tall for its legs. Twelve cells by three and a half rows, with
// room above for arms held up and a laptop held overhead.
// Units go in halves (one grid pixel) where a move wants it: a glance, a step.

/** Fills units [x0, x1) across and rows [y0, y1) down. */
function units(fill: (x0: number, y0: number, x1: number, y1: number, p?: string) => void) {
  return (x0: number, y0: number, x1: number, y1: number, p = 'o') => {
    if (x1 > x0 && y1 > y0) fill(Math.round(2 * x0), y0, Math.round(2 * x1) - 1, y1 - 1, p)
  }
}

// ─── Clawd facing front, posed ─────────────────────────────────────────────────────────────

const REST_X = 13 // the body's left edge at rest, in units
const TOP = 3 // the body's top row at rest; the ones above are for arms held up

export type Arm = 'out' | 'raised' | 'up' | 'down'

export type Pose = {
  /** Eyes moved left or right inside the face, by half units. */
  look?: -1 | 0 | 1
  isBlinking?: boolean
  /** The far eye screwed to a dash, as Clawd turns. */
  isSquinting?: boolean
  left?: Arm
  right?: Arm
  /** Whole body moved sideways, in units (halves allowed). */
  dx?: number
  /** Whole body, legs and all, up off the floor by rows: a hop. */
  lift?: number
  /** The body sunk onto its legs by a row: a crouch, or a landing. */
  squash?: boolean
  /** The body raised on longer legs by a row: a stretch. */
  stretch?: boolean
  /** Feet drawn up under the body, as in the air. */
  isTucked?: boolean
  /** Legs stepped half a unit to one side, for walking. */
  step?: -1 | 0 | 1
}

// An arm's units across, as [from, to) off the body's left edge (the body is 0 to 8), and
// its rows down from the body's top. The right arm is the mirror image.
const ARMS: Record<Arm, { x: [number, number]; y: [number, number] }> = {
  out: { x: [-2, 0], y: [2, 4] }, // straight out from the side
  raised: { x: [-2, 0], y: [1, 3] }, // out, a row higher: between out and up
  up: { x: [0, 2], y: [-2, 0] }, // up off the top corner, the desktop's hop
  down: { x: [-1, 0], y: [3, 5] }, // hanging down the side
}

export function poseGrid(pose: Pose = {}): Grid {
  const { fill, grid } = canvas()
  const u = units(fill)
  const x0 = REST_X + (pose.dx ?? 0)
  const lift = pose.lift ?? 0
  const rise = (pose.stretch ? 1 : 0) + lift
  const top = TOP - rise + (pose.squash ? 1 : 0)
  const bottom = TOP + 5 - rise // the row under the body

  u(x0, top, x0 + 8, bottom)

  if (!pose.isBlinking) {
    const look = (pose.look ?? 0) / 2
    u(x0 + 1 + look, top + 1, x0 + 2 + look, top + 2, 'e')
    if (pose.isSquinting) u(x0 + 5.5 + look, top + 1, x0 + 7 + look, top + 2, 'e')
    else u(x0 + 6 + look, top + 1, x0 + 7 + look, top + 2, 'e')
  }

  for (const [kind, side] of [
    [pose.left ?? 'out', -1],
    [pose.right ?? 'out', 1],
  ] as const) {
    const { x, y } = ARMS[kind]
    const [from, to] = side < 0 ? x : [8 - x[1], 8 - x[0]]
    u(x0 + from, top + y[0], x0 + to, top + y[1])
  }

  // Four legs a unit wide, the outer ones under the body's edges, down to the floor; a row
  // long when tucked up in the air.
  const step = (pose.step ?? 0) / 2
  const feet = pose.isTucked ? bottom + 1 : HEIGHT - lift
  for (const lx of [0, 2, 5, 7]) u(x0 + lx + step, bottom, x0 + lx + 1 + step, feet)

  return grid()
}

/** One step of an animation: a drawing held for some milliseconds. */
export type Frame = readonly [Grid, number]

const shots = (frames: readonly (readonly [Pose, number])[]): Frame[] => frames.map(([p, ms]) => [poseGrid(p), ms])

const REST: Pose = {}
export const AT_REST = poseGrid()

/** Each animation starts from rest and comes back to it. */
export const ANIMATIONS: Record<string, readonly Frame[]> = {
  blink: shots([[{ isBlinking: true }, 130], [REST, 0]]),

  doubleBlink: shots([[{ isBlinking: true }, 110], [REST, 130], [{ isBlinking: true }, 110], [REST, 0]]),

  lookAround: shots([
    [{ look: -1 }, 900],
    [REST, 250],
    [{ look: 1 }, 900],
    [{ look: 1, isBlinking: true }, 120],
    [REST, 0],
  ]),

  wave: shots([
    [{ right: 'raised' }, 90],
    [{ right: 'up' }, 200],
    [{ right: 'raised' }, 110],
    [{ right: 'up' }, 200],
    [{ right: 'raised' }, 110],
    [{ right: 'up' }, 200],
    [{ right: 'raised' }, 90],
    [REST, 0],
  ]),

  waveLeft: shots([
    [{ left: 'raised', look: -1 }, 90],
    [{ left: 'up', look: -1 }, 200],
    [{ left: 'raised', look: -1 }, 110],
    [{ left: 'up', look: -1 }, 200],
    [{ left: 'raised', look: -1 }, 110],
    [{ left: 'up', look: -1 }, 200],
    [{ left: 'raised', look: -1 }, 90],
    [REST, 0],
  ]),

  jump: shots([
    [{ squash: true, left: 'down', right: 'down' }, 140],
    [{ lift: 1, isTucked: true, left: 'raised', right: 'raised' }, 70],
    [{ lift: 2, isTucked: true }, 160],
    [{ lift: 1, isTucked: true, left: 'raised', right: 'raised' }, 70],
    [{ squash: true, left: 'down', right: 'down' }, 120],
    [REST, 160],
    [{ squash: true, left: 'down', right: 'down' }, 140],
    [{ lift: 1, isTucked: true, left: 'raised', right: 'raised' }, 70],
    [{ lift: 2, isTucked: true }, 160],
    [{ lift: 1, isTucked: true, left: 'raised', right: 'raised' }, 70],
    [{ squash: true, left: 'down', right: 'down' }, 120],
    [REST, 0],
  ]),

  // Arms up, eyes shut; the body keeps its height, which taller reads as a tower.
  stretch: shots([
    [{ left: 'raised', right: 'raised' }, 150],
    [{ left: 'up', right: 'up' }, 150],
    [{ left: 'up', right: 'up', isBlinking: true }, 900],
    [{ left: 'up', right: 'up' }, 200],
    [{ left: 'raised', right: 'raised' }, 150],
    [REST, 0],
  ]),

  shuffle: shots([
    [{ look: -1 }, 120],
    [{ look: -1, step: -1 }, 140],
    [{ dx: -0.5, look: -1 }, 140],
    [{ dx: -1, look: -1, step: -1 }, 140],
    [{ dx: -1.5, look: -1 }, 140],
    [{ dx: -2, look: -1 }, 450],
    [{ dx: -2, look: 1 }, 350],
    [{ dx: -1.5, look: 1, step: 1 }, 140],
    [{ dx: -1, look: 1 }, 140],
    [{ dx: -0.5, look: 1, step: 1 }, 140],
    [{ look: 1 }, 140],
    [{ dx: 0.5, look: 1, step: 1 }, 140],
    [{ dx: 1, look: 1 }, 140],
    [{ dx: 1.5, look: 1, step: 1 }, 140],
    [{ dx: 2, look: 1 }, 450],
    [{ dx: 2, look: -1 }, 350],
    [{ dx: 1.5, look: -1, step: -1 }, 140],
    [{ dx: 1, look: -1 }, 140],
    [{ dx: 0.5, look: -1, step: -1 }, 140],
    [{ look: -1 }, 140],
    [REST, 0],
  ]),

  dance: shots([
    [{ left: 'up', right: 'down', squash: true }, 200],
    [{ left: 'raised', right: 'raised', lift: 1, isTucked: true }, 100],
    [{ left: 'down', right: 'up', squash: true }, 200],
    [{ left: 'raised', right: 'raised', lift: 1, isTucked: true }, 100],
    [{ left: 'up', right: 'down', squash: true }, 200],
    [{ left: 'raised', right: 'raised', lift: 1, isTucked: true }, 100],
    [{ left: 'up', right: 'up', lift: 1, isTucked: true }, 250],
    [REST, 0],
  ]),

  shrug: shots([
    [{ left: 'down', right: 'down', look: 1 }, 600],
    [{ left: 'raised', right: 'raised', look: 1 }, 80],
    [{ left: 'up', right: 'up', squash: true }, 350],
    [{ left: 'raised', right: 'raised' }, 80],
    [REST, 0],
  ]),
}

/** Blinks come up often, as they would; the bigger moves less so. */
const WEIGHTS: Record<string, number> = {
  blink: 5,
  doubleBlink: 2,
  lookAround: 3,
  wave: 2,
  waveLeft: 1,
  jump: 2,
  stretch: 1,
  shuffle: 2,
  dance: 1,
  shrug: 1,
}

// ─── At the laptop ─────────────────────────────────────────────────────────────────────────
//
// As the desktop app's Clawd does it: turns with a squint, lifts the laptop out and over its
// head, swings it down open onto the floor (a grey "\_"), hops into a crouch and types side
// on, its far side in shade, its legs bent under it, one hand then the other tapping keys.

const SIDE_X = 15 // the crouched body's left edge, in units
const HINGE = SIDE_X - 5 // where the screen meets the keyboard

/** The laptop open on the floor, a key lit (its unit) if one is pressed. */
function laptopOpen(lit?: number): Grid {
  const { fill, grid } = canvas()
  const u = units(fill)
  // The screen, tipped back: a unit further left for each row up.
  for (let k = 1; k <= 4; k++) u(HINGE - k, HEIGHT - 1 - k, HINGE - k + 1, HEIGHT - k, 'g')
  u(HINGE, HEIGHT - 1, SIDE_X - 1, HEIGHT, 'g')
  if (lit !== undefined) u(lit, HEIGHT - 1, lit + 1, HEIGHT, 'w')
  return grid()
}

/** The laptop shut, held: tipped up at the shoulder, or flat over the head. */
function laptopHeld(where: 'shoulder' | 'overhead', x0: number): Grid {
  const { fill, grid } = canvas()
  const u = units(fill)
  if (where === 'shoulder') {
    u(x0 - 4, TOP - 1, x0 - 2, TOP, 'g')
    u(x0 - 3, TOP, x0 - 1, TOP + 1, 'g')
  } else u(x0 - 3, 0, x0 + 2, 1, 'g')
  return grid()
}

/** Both hands up, or one of them down on the keys: the near hand, or the far one. */
type Hands = 'up' | 'near' | 'far'

function typingGrid(hands: Hands, options: { isBlinking?: boolean } = {}): Grid {
  const { fill, grid } = canvas()
  const u = units(fill)
  const x0 = SIDE_X
  const top = TOP
  u(x0, top, x0 + 6, HEIGHT - 2)
  u(x0 + 6, top, x0 + 8, HEIGHT - 2, 's')

  // Eyes to the front of the face: looking at the screen.
  if (!options.isBlinking) {
    u(x0 + 0.5, top + 1, x0 + 1.5, top + 2, 'e')
    u(x0 + 4.5, top + 1, x0 + 5.5, top + 2, 'e')
  }

  // Legs bent under it: a unit down from the body, the foot a half unit back.
  for (const [lx, p] of [
    [0, 'o'],
    [2, 'o'],
    [4.5, 'o'],
    [7, 's'],
  ] as const) {
    u(x0 + lx, HEIGHT - 2, x0 + lx + 1, HEIGHT - 1, p)
    u(x0 + lx - 0.5, HEIGHT - 1, x0 + lx + 0.5, HEIGHT, p)
  }

  // The hands, off the front: waiting, the near one over the far one (in shade); pressing,
  // one comes down onto a key from its wrist, the other waits.
  if (hands !== 'far') u(x0 - 2, HEIGHT - 4, x0, HEIGHT - 3)
  u(x0 - 2, HEIGHT - 3, x0, HEIGHT - 2, 's')
  if (hands === 'near') {
    u(x0 - 1, HEIGHT - 3, x0, HEIGHT - 2)
    u(x0 - 3, HEIGHT - 2, x0 - 1, HEIGHT - 1)
  }
  if (hands === 'far') u(x0 - 4, HEIGHT - 2, x0 - 2, HEIGHT - 1, 's')

  const lit = hands === 'near' ? x0 - 3 : hands === 'far' ? x0 - 4 : undefined
  return overlay(grid(), laptopOpen(lit))
}

const UP = typingGrid('up')
const NEAR = typingGrid('near')
const FAR = typingGrid('far')
const UP_BLINK = typingGrid('up', { isBlinking: true })
const NEAR_BLINK = typingGrid('near', { isBlinking: true })

// Clawd stays put to lift the laptop, then steps right a unit as it sets it down, clear of the
// keyboard, and another as it hops into the crouch.
const TURNED: Pose = { look: -1, isSquinting: true, left: 'down' }
const AT_SHOULDER = overlay(poseGrid({ ...TURNED, left: 'raised' }), laptopHeld('shoulder', REST_X))
const OVERHEAD = overlay(poseGrid({ ...TURNED, left: 'up' }), laptopHeld('overhead', REST_X))
const SET_DOWN = overlay(poseGrid({ dx: 1, look: -1, left: 'down' }), laptopOpen())
const HOP = overlay(poseGrid({ dx: 1, look: -1, stretch: true, left: 'up', right: 'up' }), laptopOpen())

/** Clawd turns, lifts the laptop out and overhead, sets it down open and hops to it. */
export const TAKE_OUT: readonly Frame[] = [
  [poseGrid({ look: -1 }), 120],
  [poseGrid(TURNED), 280],
  [AT_SHOULDER, 120],
  [OVERHEAD, 260],
  [SET_DOWN, 220],
  [HOP, 110],
  [UP, 150],
]

/** And the other way: stands, lifts the laptop shut overhead, puts it away, turns back. */
export const PUT_AWAY: readonly Frame[] = [
  [HOP, 110],
  [SET_DOWN, 180],
  [OVERHEAD, 220],
  [AT_SHOULDER, 120],
  [poseGrid(TURNED), 200],
  [poseGrid({ look: -1 }), 120],
  [AT_REST, 0],
]

// Clawd types the whole turn through, but not like a metronome: fast bursts, steadier
// patches, a blink between keys, now and then a look at what it wrote.
export const TYPING: Record<string, readonly Frame[]> = {
  // Hand over hand, with a beat of both up between some keys.
  burst: [[NEAR, 80], [FAR, 80], [NEAR, 80], [FAR, 80], [NEAR, 80], [UP, 60], [FAR, 80], [NEAR, 80], [UP, 60]],
  steady: [[NEAR, 140], [UP, 110], [FAR, 140], [UP, 110], [NEAR, 140], [UP, 110], [FAR, 140], [UP, 110]],
  blink: [[NEAR, 100], [UP_BLINK, 130], [NEAR_BLINK, 100], [FAR, 100], [UP, 100]],
  read: [[UP, 700], [UP_BLINK, 120], [UP, 400]],
}

const TYPING_WEIGHTS: Record<string, number> = { burst: 5, steady: 4, blink: 2, read: 1 }

/** The next patch of typing, `roll` in [0, 1). */
export function pickTyping(roll: number): string {
  return weighted(Object.keys(TYPING), TYPING_WEIGHTS, roll)
}

/** Picks an animation by weight, `roll` in [0, 1); never the one just played, when there is a choice. */
export function pick(roll: number, last: string | null): string {
  return weighted(Object.keys(ANIMATIONS).filter(n => n !== last), WEIGHTS, roll)
}

function weighted(names: readonly string[], weights: Record<string, number>, roll: number): string {
  const total = names.reduce((sum, n) => sum + (weights[n] ?? 1), 0)
  let left = roll * total
  for (const name of names) {
    left -= weights[name] ?? 1
    if (left < 0) return name
  }
  return names[names.length - 1] ?? 'blink'
}

/** How long Clawd rests between animations, `roll` in [0, 1): 3 to 9 seconds. */
export function restMs(roll: number): number {
  return 3000 + Math.floor(roll * 6000)
}

/** Every frame of every animation, for checks over all of them. */
export const ALL_FRAMES: readonly Frame[] = [...Object.values(ANIMATIONS), ...Object.values(TYPING), TAKE_OUT, PUT_AWAY].flat()
