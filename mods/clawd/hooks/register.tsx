import { atom, read, update } from 'claude-code'
import type { Register, Timer } from 'claude-code'

import { ANIMATIONS, TYPING, draw, pick, pickTyping, restMs } from './sprite'
import type { Frame, Pose } from './sprite'

const sprite = atom({ plugin: 'clawd', key: 'sprite' } as const, null)
const isHidden = atom({ plugin: 'clawd', key: 'isHidden' } as const, false)

const REST = draw()
const COLUMNS = REST[0]?.reduce((sum, run) => sum + run.text.length, 0) ?? 0

// Clawd keeps to the right of what the band already shows, and leaves the band alone when
// that would squeeze it under this many columns.
const MIN_COLUMNS = 40

const COLOR = { clawd: 'claude', laptop: 'inactive' } as const

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
    let isTyping = false

    const after = (ms: number, fn: () => void) => {
      timer?.cancel()
      timer = $.clock.after(ms, fn)
    }
    const show = (pose: Pose) => void update($, sprite, () => draw(pose))

    const play = (frames: readonly Frame[], at: number, then: () => void): void => {
      const frame = frames[at]
      if (frame === undefined) return then()
      show(frame[0])
      after(frame[1], at === frames.length - 1 ? then : () => play(frames, at + 1, then))
    }
    const rest = () =>
      after(restMs(Math.random()), () => {
        last = pick(Math.random(), last)
        play(ANIMATIONS[last] ?? [], 0, rest)
      })
    const type = (): void => play(TYPING[pickTyping(Math.random())] ?? [], 0, type)

    // Called while the band draws, which writes no state: the change lands on the next tick.
    setTyping = working => {
      if (working === isTyping) return
      isTyping = working
      after(0, () => {
        if (working) return type()
        show({})
        rest()
      })
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
                <Text key={`run-${j}`} color={COLOR[run.tone]}>
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
