import type { Sprite } from '../types'

// Clawd is drawn on a grid of pixels, two across and two down per terminal cell, with the
// quadrant blocks the Claude Code logo itself uses. At rest it is that logo, cell for cell:
//    ▐▛███▜▌
//   ▝▜█████▛▘
//     ▘▘ ▝▝
// with one empty column either side so it can shuffle sideways.

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

export const WIDTH = 22 // pixels: 11 cells
export const HEIGHT = 6 // pixels: 3 rows
const LEFT = 2 // where the logo's own column 0 sits at rest

// Bits of a cell: top-left, top-right, bottom-left, bottom-right.
const QUADRANT = [' ', '▘', '▝', '▀', '▖', '▌', '▞', '▛', '▗', '▚', '▐', '▜', '▄', '▙', '▟', '█']

export function draw(pose: Pose = {}): Sprite {
  const on = new Array<boolean>(WIDTH * HEIGHT).fill(false)
  const x0 = LEFT + (pose.dx ?? 0)
  const set = (x: number, y: number, value = true) => {
    const px = x0 + x
    if (px >= 0 && px < WIDTH && y >= 0 && y < HEIGHT) on[y * WIDTH + px] = value
  }
  const bit = (x: number, y: number, value: number) => (on[y * WIDTH + x] ? value : 0)

  // Head and body: columns 3-14, rows 0-3; the arms' row reaches out to 1-16.
  for (let y = 0; y <= 3; y++) for (let x = 3; x <= 14; x++) set(x, y)

  // Eyes are holes in row 1; shut, the face is plain.
  if (!pose.isBlinking) {
    const look = pose.look ?? 0
    set(5 + look, 1, false)
    set(12 + look, 1, false)
  }

  arm(pose.left ?? 'out', 2, 1, set)
  arm(pose.right ?? 'out', 15, 16, set)

  const step = pose.step ?? 0
  if (!pose.isTucked) for (const x of [4, 6, 11, 13]) set(x + step, 4)

  const rows: string[] = []
  for (let r = 0; r < HEIGHT / 2; r++) {
    let row = ''
    for (let c = 0; c < WIDTH / 2; c++) {
      const x = 2 * c
      const y = 2 * r
      row += QUADRANT[bit(x, y, 1) | bit(x + 1, y, 2) | bit(x, y + 1, 4) | bit(x + 1, y + 1, 8)]
    }
    rows.push(row)
  }
  return rows
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

/** One step of an animation: a pose held for some milliseconds. */
export type Frame = [Pose, number]

const REST: Pose = {}

/** Each animation starts from rest and comes back to it. */
export const ANIMATIONS: Record<string, readonly Frame[]> = {
  blink: [[{ isBlinking: true }, 140], [REST, 0]],

  doubleBlink: [[{ isBlinking: true }, 120], [REST, 140], [{ isBlinking: true }, 120], [REST, 0]],

  lookAround: [
    [{ look: -1 }, 900],
    [REST, 250],
    [{ look: 1 }, 900],
    [{ look: 1, isBlinking: true }, 130],
    [REST, 0],
  ],

  wave: [
    [{ right: 'up' }, 220],
    [{ right: 'out' }, 180],
    [{ right: 'up' }, 220],
    [{ right: 'out' }, 180],
    [{ right: 'up' }, 220],
    [REST, 0],
  ],

  waveLeft: [
    [{ left: 'up', look: -1 }, 220],
    [{ left: 'out', look: -1 }, 180],
    [{ left: 'up', look: -1 }, 220],
    [{ left: 'out', look: -1 }, 180],
    [{ left: 'up', look: -1 }, 220],
    [REST, 0],
  ],

  jump: [
    [{ isTucked: true, left: 'up', right: 'up' }, 160],
    [REST, 160],
    [{ isTucked: true, left: 'up', right: 'up' }, 160],
    [REST, 160],
    [{ isTucked: true, left: 'up', right: 'up' }, 160],
    [REST, 0],
  ],

  stretch: [
    [{ left: 'up', right: 'up', isBlinking: true }, 900],
    [{ left: 'up', right: 'up' }, 200],
    [REST, 0],
  ],

  shuffle: [
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
  ],

  dance: [
    [{ left: 'up', right: 'down', isTucked: true }, 200],
    [{ left: 'down', right: 'up' }, 200],
    [{ left: 'up', right: 'down', isTucked: true }, 200],
    [{ left: 'down', right: 'up' }, 200],
    [{ left: 'up', right: 'up', isTucked: true }, 200],
    [REST, 0],
  ],

  shrug: [
    [{ left: 'down', right: 'down', look: 1 }, 700],
    [{ left: 'up', right: 'up' }, 300],
    [REST, 0],
  ],
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

/** Picks an animation by weight, `roll` in [0, 1); never the one just played, when there is a choice. */
export function pick(roll: number, last: string | null): string {
  const names = Object.keys(ANIMATIONS).filter(n => n !== last)
  const total = names.reduce((sum, n) => sum + (WEIGHTS[n] ?? 1), 0)
  let left = roll * total
  for (const name of names) {
    left -= WEIGHTS[name] ?? 1
    if (left < 0) return name
  }
  return names[names.length - 1] ?? 'blink'
}

/** How long Clawd rests between animations, `roll` in [0, 1): 3 to 9 seconds. */
export function restMs(roll: number): number {
  return 3000 + Math.floor(roll * 6000)
}
