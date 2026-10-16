import { atom, read, update } from 'claude-code'
import type { Register, Timer } from 'claude-code'

import { ANIMATIONS, PUT_AWAY, TAKE_OUT, TYPING, draw, pick, pickTyping, restMs } from './sprite'
import type { Frame } from './sprite'
import type { Sprite, Tone } from '../types'

const sprite = atom({ plugin: 'clawd', key: 'sprite' } as const, null)
const isHidden = atom({ plugin: 'clawd', key: 'isHidden' } as const, false)

const REST = draw()
const COLUMNS = REST[0]?.reduce((sum, run) => sum + run.text.length, 0) ?? 0

// Clawd keeps to the right of what the band already shows, and leaves the band alone when
// that would squeeze it under this many columns.
const MIN_COLUMNS = 40

// The shaded side is a fixed darker orange: a dimmed 'claude' is drawn grey in some terminals.
const COLOR: Record<Tone, { color: string }> = {
  clawd: { color: 'claude' },
  shade: { color: '#a8563c' },
  laptop: { color: 'inactive' },
  key: { color: 'text' },
}

export const register: Register = on => {
  // One timer at a time: a rest, or the next frame of an animation.
  let timer: Timer | null = null
  // Idle, Clawd rests and now and then plays an animation; while Claude works, it types.
  // Set by session.start, where the loop lives; the band calls it as turns start and end.
  let setTyping: (working: boolean) => void = () => {}

  on('session.start', async ($, e, next) => {
    timer?.cancel()
    const surfaces = await $.session.surfaces()
    if (!surfaces.includes('terminal')) return next(e)

    let last: string | null = null
    // Whether Claude is working, as the band last said; and whether the laptop is out, which
    // runs from the take-out to the put-away.
    let isWorking = false
    let isAtLaptop = false
    // How long the laptop has been out with Claude not working, counted in frames shown.
    let idleMs = 0

    const after = (ms: number, fn: () => void) => {
      timer?.cancel()
      timer = $.clock.after(ms, fn)
    }
    const show = (drawing: Sprite) => void update($, sprite, () => drawing)

    const play = (frames: readonly Frame[], at: number, then: () => void): void => {
      const frame = frames[at]
      if (frame === undefined) return then()
      show(frame[0])
      if (isAtLaptop && !isWorking) idleMs += frame[1]
      after(frame[1], at === frames.length - 1 ? then : () => play(frames, at + 1, then))
    }
    const rest = () =>
      after(restMs(Math.random()), () => {
        last = pick(Math.random(), last)
        play(ANIMATIONS[last] ?? [], 0, rest)
      })
    // Between one patch of typing and the next, Clawd looks up to see whether the turn is over,
    // and puts the laptop away only once Claude has not been working for a second. A moment's
    // pause in a turn never has it put away and taken out again.
    const type = (): void => {
      if (isWorking || idleMs < 1000) return play(TYPING[pickTyping(Math.random())] ?? [], 0, type)
      isAtLaptop = false
      play(PUT_AWAY, 0, rest)
    }

    // Called while the band draws, which writes no state: the laptop comes out on the next
    // tick, cutting short whatever idle animation was playing.
    setTyping = working => {
      isWorking = working
      if (working) idleMs = 0
      if (!working || isAtLaptop) return
      isAtLaptop = true
      after(0, () => play(TAKE_OUT, 0, type))
    }

    await $.command.register({
      name: 'clawd',
      description: 'Show or hide Clawd above the prompt.',
      argumentHint: '[show|hide]',
    })
    await update($, sprite, () => REST)
    rest()
    return next(e)
  })

  on('session.end', async ($, e, next) => {
    timer?.cancel()
    timer = null
    return next(e)
  })

  on('command.run', { command: 'clawd' }, async ($, e) => {
    const arg = e.args.trim().toLowerCase()
    const hide = arg === 'hide' ? true : arg === 'show' ? false : !(await read($, isHidden))
    await update($, isHidden, () => hide)
    return { text: hide ? 'Clawd is hiding.' : 'Clawd is back.' }
  })

  // Whatever the band holds (the task list, or nothing) keeps its place on the left; Clawd
  // stands at the right end, feet on the prompt's top border.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.surface !== 'terminal' || e.props.hasSurvey) return next(e)
    if (e.props.maxRows < REST.length || e.props.bodyColumns < MIN_COLUMNS) return next(e)
    if (await read($, isHidden)) return next(e)
    // The band is drawn again whenever a turn starts or ends: the one place that says so.
    setTyping(e.props.isWorking)
    const rows = (await read($, sprite)) ?? REST
    const beneath = await next(e)

    const { Box, Text } = $.ui.resolve(e)
    return (
      // No grow on the left: when another mod wraps this tree in a row of its own, Clawd's
      // part keeps to its own width rather than squeezing that mod's column.
      <Box flexDirection="row" alignItems="flex-end" justifyContent="space-between">
        <Box key="beneath" flexShrink={1}>
          {beneath}
        </Box>
        <Box key="clawd" flexDirection="column" flexShrink={0} width={COLUMNS}>
          {rows.map((row, i) => (
            <Text key={`row-${i}`} wrap="truncate-end">
              {row.map((run, j) => (
                <Text key={`run-${j}`} {...COLOR[run.tone]}>
                  {run.text}
                </Text>
              ))}
            </Text>
          ))}
        </Box>
      </Box>
    )
  })
}
