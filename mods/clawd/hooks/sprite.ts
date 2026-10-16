import type { Run, Sprite, Tone } from '../types'

// Clawd is drawn on a grid of pixels, two across and two down per terminal cell, with the
// quadrant blocks the Claude Code logo itself uses. At rest it is that logo, cell for cell:
//    ▐▛███▛█
//   ▝▜██████▀
//    ▝▝   ▝▝
// its outer legs straight down from the sides of its body.
// with room either side to shuffle, and on its left for the laptop. While Claude works it
// does what the desktop app's Clawd does: turns, takes out a laptop, sets it open on the
// floor and crouches over it, side on, tapping the keys.

export const WIDTH = 30 // pixels: 15 cells
export const HEIGHT = 6 // pixels: 3 rows
const LEFT = 10 // where the logo's own column 0 sits at rest

// A grid is HEIGHT strings of WIDTH pixels: '.' empty, 'o' Clawd, 's' Clawd's side in shade,
// 'g' the laptop, 'w' a key lit as it is pressed. A cell takes one colour, so the pixels that
// share a cell share a tone.
export type Grid = readonly string[]

const TONES: Record<string, Tone> = { o: 'clawd', s: 'shade', g: 'laptop', w: 'key' }

// Bits of a cell: top-left, top-right, bottom-left, bottom-right.
const QUADRANT = [' ', '▘', '▝', '▀', '▖', '▌', '▞', '▛', '▗', '▚', '▐', '▜', '▄', '▙', '▟', '█']

export function fromGrid(grid: Grid): Sprite {
  const at = (x: number, y: number) => grid[y]?.[x] ?? '.'
  const rows: Run[][] = []
  for (let r = 0; r < HEIGHT / 2; r++) {
    const runs: Run[] = []
    for (let c = 0; c < WIDTH / 2; c++) {
      const pixels = [at(2 * c, 2 * r), at(2 * c + 1, 2 * r), at(2 * c, 2 * r + 1), at(2 * c + 1, 2 * r + 1)]
      const lit = pixels.find(p => p !== '.')
      const tone = TONES[lit ?? 'o'] ?? 'clawd'
      const bits = pixels.reduce((sum, p, i) => (p === '.' ? sum : sum | (1 << i)), 0)
      const cell = QUADRANT[bits] ?? ' '
      const isSolid = lit !== undefined && isSolidAt(at, c, r)
      const prev = runs[runs.length - 1]
      if (prev !== undefined && prev.tone === tone && prev.isSolid === isSolid) {
        runs[runs.length - 1] = { tone, isSolid, text: prev.text + cell }
      } else runs.push({ tone, isSolid, text: cell })
    }
    rows.push(runs)
  }
  return rows
}

// Some terminals, macOS Terminal among them, draw the blocks from the font, and a font's
// blocks can fall short of the row: a gap above each one and a smaller one below, the row's
// line spacing. Drawn so, Clawd is cut into stripes. A cell's background fills the whole row,
// gaps and all, so a cell whose top is lit across is drawn solid, and fills the gap between it
// and what is lit above it; Clawd's top row is drawn so too, for one even top edge. A cell lit
// on top with nothing above it (an arm held out) stays a glyph and keeps its own height.
// Where the blocks fill the row both ways look alike.
function isSolidAt(at: (x: number, y: number) => string, c: number, r: number): boolean {
  const [left, right] = [2 * c, 2 * c + 1]
  if (at(left, 2 * r) === '.' || at(right, 2 * r) === '.') return false
  return r === 0 || at(left, 2 * r - 1) !== '.' || at(right, 2 * r - 1) !== '.'
}

/** A solid run's text as drawn: the cells' empty quadrants, each where its glyph had blocks. */
export function inverted(text: string): string {
  return [...text].map(cell => QUADRANT[15 ^ QUADRANT.indexOf(cell)] ?? ' ').join('')
}

/** Cells whose pixels are of more than one tone: what `fromGrid` cannot draw truly. */
export function mixedCells(grid: Grid): string[] {
  const mixed: string[] = []
  for (let r = 0; r < HEIGHT / 2; r++) {
    for (let c = 0; c < WIDTH / 2; c++) {
      const tones = new Set(
        [0, 1].flatMap(dy => [0, 1].map(dx => grid[2 * r + dy]?.[2 * c + dx] ?? '.')).filter(p => p !== '.'),
      )
      if (tones.size > 1) mixed.push(`row ${r} cell ${c}`)
    }
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

/** A sprite's rows as plain text, colours dropped. */
export function plain(sprite: Sprite): string[] {
  return sprite.map(row => row.map(run => run.text).join(''))
}

// ─── Clawd facing front, posed ─────────────────────────────────────────────────────────────

export type Arm = 'out' | 'up' | 'down'

export type Pose = {
  /** Eyes moved left (-1) or right (1) inside the face. */
  look?: -1 | 0 | 1
  isBlinking?: boolean
  left?: Arm
  right?: Arm
  /** Whole body moved sideways a cell (two pixels); a single pixel breaks the blocks apart. */
  dx?: -2 | 0 | 2
  /** Feet drawn up, as at the top of a jump: a cell can't move half a row and stay crisp. */
  isTucked?: boolean
  /** Legs stepped to one side, for walking. */
  step?: -1 | 0 | 1
}

export function poseGrid(pose: Pose = {}): Grid {
  const on = Array.from({ length: HEIGHT }, () => new Array<string>(WIDTH).fill('.'))
  const x0 = LEFT + (pose.dx ?? 0)
  const set = (x: number, y: number, p = 'o') => {
    const row = on[y]
    if (row !== undefined && x0 + x >= 0 && x0 + x < WIDTH) row[x0 + x] = p
  }

  // Head and body: columns 3-15, rows 0-3; the arms' row reaches out to 1-17.
  for (let y = 0; y <= 3; y++) for (let x = 3; x <= 15; x++) set(x, y)

  // Eyes are holes in row 1; shut, the face is plain.
  if (!pose.isBlinking) {
    const look = pose.look ?? 0
    set(5 + look, 1, '.')
    set(13 + look, 1, '.')
  }

  arm(pose.left ?? 'out', 2, 1, set)
  arm(pose.right ?? 'out', 16, 17, set)

  const step = pose.step ?? 0
  // Two pairs, the outer leg of each under the body's edge.
  if (!pose.isTucked) for (const x of [3, 5, 13, 15]) set(x + step, 4)

  return on.map(row => row.join(''))
}

export function draw(pose: Pose = {}): Sprite {
  return fromGrid(poseGrid(pose))
}

/** An arm is two pixels: `near` against the body, `far` its tip. */
function arm(kind: Arm, near: number, far: number, set: (x: number, y: number) => void) {
  if (kind === 'out') {
    set(near, 2)
    set(far, 2)
  } else if (kind === 'up') {
    set(near, 1)
    set(far, 0)
  } else {
    set(near, 3)
    set(far, 3)
  }
}

/** One step of an animation: a drawing held for some milliseconds. */
export type Frame = readonly [Sprite, number]

const shots = (frames: readonly (readonly [Pose, number])[]): Frame[] => frames.map(([p, ms]) => [draw(p), ms])

const REST: Pose = {}

/** Each animation starts from rest and comes back to it. */
export const ANIMATIONS: Record<string, readonly Frame[]> = {
  blink: shots([[{ isBlinking: true }, 140], [REST, 0]]),

  doubleBlink: shots([[{ isBlinking: true }, 120], [REST, 140], [{ isBlinking: true }, 120], [REST, 0]]),

  lookAround: shots([
    [{ look: -1 }, 900],
    [REST, 250],
    [{ look: 1 }, 900],
    [{ look: 1, isBlinking: true }, 130],
    [REST, 0],
  ]),

  wave: shots([
    [{ right: 'up' }, 220],
    [{ right: 'out' }, 180],
    [{ right: 'up' }, 220],
    [{ right: 'out' }, 180],
    [{ right: 'up' }, 220],
    [REST, 0],
  ]),

  waveLeft: shots([
    [{ left: 'up', look: -1 }, 220],
    [{ left: 'out', look: -1 }, 180],
    [{ left: 'up', look: -1 }, 220],
    [{ left: 'out', look: -1 }, 180],
    [{ left: 'up', look: -1 }, 220],
    [REST, 0],
  ]),

  jump: shots([
    [{ isTucked: true, left: 'up', right: 'up' }, 160],
    [REST, 160],
    [{ isTucked: true, left: 'up', right: 'up' }, 160],
    [REST, 160],
    [{ isTucked: true, left: 'up', right: 'up' }, 160],
    [REST, 0],
  ]),

  stretch: shots([
    [{ left: 'up', right: 'up', isBlinking: true }, 900],
    [{ left: 'up', right: 'up' }, 200],
    [REST, 0],
  ]),

  shuffle: shots([
    [{ look: -1, step: -1 }, 180],
    [{ dx: -2, look: -1 }, 260],
    [{ dx: -2, look: -1, step: 1 }, 180],
    [{ dx: -2, look: -1 }, 400],
    [{ dx: -2, look: 1 }, 300],
    [{ look: 1, step: 1 }, 180],
    [{ dx: 2, look: 1 }, 260],
    [{ dx: 2, look: 1, step: -1 }, 180],
    [{ dx: 2, look: 1 }, 400],
    [{ dx: 2, look: -1 }, 300],
    [{ look: -1, step: -1 }, 180],
    [REST, 0],
  ]),

  dance: shots([
    [{ left: 'up', right: 'down', isTucked: true }, 200],
    [{ left: 'down', right: 'up' }, 200],
    [{ left: 'up', right: 'down', isTucked: true }, 200],
    [{ left: 'down', right: 'up' }, 200],
    [{ left: 'up', right: 'up', isTucked: true }, 200],
    [REST, 0],
  ]),

  shrug: shots([
    [{ left: 'down', right: 'down', look: 1 }, 700],
    [{ left: 'up', right: 'up' }, 300],
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
// Drawn pixel by pixel after the desktop app's: the laptop open on the floor like "\_", and
// Clawd crouched side on, its far side in shade, one hand coming down on the keys.

//                  0         1         2
//                  0123456789012345678901234567
const LAPTOP_DOWN = [
  '............................',
  '............................',
  'g...........................',
  '.g..........................',
  '..g.........................',
  '..gggggg....................',
]

// Held up, about to be set down (or just picked up).
const LAPTOP_UP = [
  '....g.......................',
  '.....ggggg..................',
  '............................',
  '............................',
  '............................',
  '............................',
]

/** Both hands up, or one of them down on the keys: the near hand, or the far one. */
type Hands = 'up' | 'near' | 'far'

// Side on, Clawd is as wide as from the front, 13 pixels (columns 13-25), its last cell its far
// side in shade. Its legs go straight down from both sides, as at the front. Its two hands
// make a block on its front, one above the other (columns 10-12, rows 2-3), as on the desktop
// app; to type, one comes down onto the keys (row 4) while the other stays up. The hand that
// comes down lands in the cell at the keyboard's end, a cell clear of the legs, which hold
// still the whole time.
//      ▐▜██▜██          ▐▜██▜██          ▐▜██▜██
//  ▚   ████████     ▚    ▀███████    ▚    ▄███████
//   ▙▄▄  ▝▝   ▝▝     ▙▄▄▀ ▝▝   ▝▝     ▙▄▄▀ ▝▝   ▝▝
//    both up          near down        far down
function typingGrid(hands: Hands, options: { isBlinking?: boolean } = {}): Grid {
  const on = Array.from({ length: HEIGHT }, () => new Array<string>(WIDTH).fill('.'))
  const set = (x: number, y: number, p: string) => {
    const row = on[y]
    if (row !== undefined) row[x] = p
  }
  for (let y = 0; y <= 3; y++) {
    for (let x = 13; x <= 23; x++) set(x, y, 'o')
    set(24, y, 's')
    set(25, y, 's')
  }
  if (!options.isBlinking) {
    // Both to the left of their cells: looking at the screen.
    set(14, 1, '.')
    set(20, 1, '.')
  }
  // The wrists, and the hands that are up: the near one in row 2, the far one in row 3.
  set(12, 2, 'o')
  set(12, 3, 'o')
  if (hands !== 'far') {
    set(10, 2, 'o')
    set(11, 2, 'o')
  }
  if (hands !== 'near') {
    set(10, 3, 'o')
    set(11, 3, 'o')
  }
  if (hands !== 'up') {
    set(8, 4, 'o')
    set(9, 4, 'o')
  }
  for (const x of [13, 15, 23]) set(x, 4, 'o')
  set(25, 4, 's') // the far-side leg, in shade
  const crouched = on.map(row => row.join(''))
  const keys = hands !== 'up' ? LAPTOP_DOWN.map((row, y) => (y === 5 ? '..ggggww....................' : row)) : LAPTOP_DOWN
  return overlay(crouched, keys)
}

const UP = fromGrid(typingGrid('up'))
const NEAR = fromGrid(typingGrid('near'))
const FAR = fromGrid(typingGrid('far'))
const UP_BLINK = fromGrid(typingGrid('up', { isBlinking: true }))
const NEAR_BLINK = fromGrid(typingGrid('near', { isBlinking: true }))

const HOLDING = overlay(poseGrid({ look: -1, left: 'up' }), LAPTOP_UP)
const SET_DOWN = overlay(poseGrid({ look: -1 }), LAPTOP_DOWN)

/** Clawd turns, takes the laptop out, sets it down and crouches to it. */
export const TAKE_OUT: readonly Frame[] = [
  [draw({ look: -1 }), 300],
  [fromGrid(HOLDING), 350],
  [fromGrid(SET_DOWN), 250],
  [UP, 150],
]

/** And the other way: stands, picks the laptop up, puts it away, turns back. */
export const PUT_AWAY: readonly Frame[] = [
  [fromGrid(SET_DOWN), 200],
  [fromGrid(HOLDING), 300],
  [draw({ look: -1 }), 250],
  [draw(), 0],
]

// Clawd types the whole turn through, but not like a metronome: fast bursts, steadier
// patches, a blink between keys, now and then a look at what it wrote.
export const TYPING: Record<string, readonly Frame[]> = {
  // Hand over hand: near, far, near, far, with a beat of both up between some keys.
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

/** Every grid drawn at the laptop, for checking that no cell mixes two tones. */
export const LAPTOP_GRIDS: readonly Grid[] = [
  typingGrid('up'),
  typingGrid('near'),
  typingGrid('far'),
  typingGrid('up', { isBlinking: true }),
  typingGrid('near', { isBlinking: true }),
  HOLDING,
  SET_DOWN,
]
