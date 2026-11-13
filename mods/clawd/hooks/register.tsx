import { atom, read, update } from 'claude-code'
import type { Register, Timer } from 'claude-code'

import { ANIMATIONS, AT_REST, COLUMNS, PUT_AWAY, ROWS, TAKE_OUT, TYPING, encode, pick, pickTyping, restMs, rgba, toBase64 } from './sprite'
import type { Frame } from './sprite'
import type { Grid } from '../types'

const sprite = atom({ plugin: 'clawd', key: 'sprite' } as const, null)
const isHidden = atom({ plugin: 'clawd', key: 'isHidden' } as const, false)
// Drawn as a picture rather than cells: `/clawd image`, for terminals that show pictures
// (kitty, Ghostty). Elsewhere the picture's alt shows in its place.
const isImage = atom({ plugin: 'clawd', key: 'isImage' } as const, false)

// Each grid pixel as a block of the picture's own: kept whole so the terminal scales it
// without blurring, three across and six down for a cell's one by two.
const IMAGE_SCALE = [3, 6] as const

// Each frame's picture, encoded once: a frame comes round many times, and its RGBA is ~37 KB.
const pictures = new Map<Grid, string>()
const picture = (grid: Grid) => {
  let hit = pictures.get(grid)
  if (hit === undefined) pictures.set(grid, (hit = toBase64(rgba(grid, ...IMAGE_SCALE))))
  return hit
}

// Clawd keeps to the right of what the band already shows, and leaves the band alone when
// that would squeeze it under this many columns.
const MIN_COLUMNS = 40
// The engine stacks one row per plugin, so Clawd's own row would sit under another mod's
// (the task list) and add its height to the band. Beside those rows instead, it hides when
// they would keep fewer than this many columns, rather than cutting their lines short.
const MIN_BESIDE = 48

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
    const show = (drawing: Grid) => void update($, sprite, () => drawing)

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
      description: 'Show or hide Clawd above the prompt, or draw it as a picture (kitty, Ghostty).',
      argumentHint: '[show|hide|image|cells]',
    })
    await update($, sprite, () => AT_REST)
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
    if (arg === 'image' || arg === 'cells') {
      await update($, isImage, () => arg === 'image')
      return {
        text:
          arg === 'image'
            ? 'Clawd is drawn as a picture. If you see the word "Clawd" instead, this terminal shows no pictures: /clawd cells.'
            : 'Clawd is drawn in cells.',
      }
    }
    const hide = arg === 'hide' ? true : arg === 'show' ? false : !(await read($, isHidden))
    await update($, isHidden, () => hide)
    return { text: hide ? 'Clawd is hiding.' : 'Clawd is back.' }
  })

  // Whatever the band holds (the task list, or nothing) keeps its place on the left; Clawd
  // stands at the right end, feet on the prompt's top border.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.surface !== 'terminal' || e.props.hasSurvey) return next(e)
    if (e.props.maxRows < ROWS || e.props.bodyColumns < MIN_COLUMNS) return next(e)
    if (await read($, isHidden)) return next(e)
    // The band is drawn again whenever a turn starts or ends: the one place that says so.
    setTyping(e.props.isWorking)
    const grid = (await read($, sprite)) ?? AT_REST
    const asImage = await read($, isImage)
    const beneath = await next(e)

    const { Box, Raster, Image } = $.ui.resolve(e)
    return (
      // No grow on the left: when another mod wraps this tree in a row of its own, Clawd's
      // part keeps to its own width rather than squeezing that mod's column.
      <Box flexDirection="row" alignItems="flex-end" justifyContent="space-between">
        <Box key="beneath" flexShrink={1}>
          {beneath}
        </Box>
        <Box key="clawd" flexShrink={0} width={COLUMNS}>
          {asImage ? (
            <Image
              key="clawd-image"
              columns={COLUMNS}
              rows={ROWS}
              alt="Clawd"
              source={{
                rgba: picture(grid),
                width: COLUMNS * 2 * IMAGE_SCALE[0],
                height: ROWS * 2 * IMAGE_SCALE[1],
              }}
            />
          ) : (
            <Raster key="clawd-cells" columns={COLUMNS} rows={ROWS} cells={encode(grid)} />
          )}
        </Box>
      </Box>
    )
  })

  // With other mods' rows in the band, Clawd stands to the right of them all, sharing their
  // rows rather than taking rows of its own under them; too narrow, it steps out of the band.
  on('ui.render', { component: 'AbovePromptList' }, async ($, e, next) => {
    if (e.surface !== 'terminal' || e.props.hasSurvey) return next(e)
    const own = e.props.rows.find(r => r.plugin === 'clawd')
    const others = e.props.rows.filter(r => r.plugin !== 'clawd')
    if (own === undefined || others.length === 0) return next(e)
    const rest = { ...e, props: { ...e.props, rows: others } }
    if (e.props.bodyColumns < COLUMNS + MIN_BESIDE) return next(rest)
    const stacked = await next(rest)
    // Clawd's own row comes back through next too: a Raster is kept only from what it returns.
    const beside = await next({ ...e, props: { ...e.props, rows: [own] } })

    const { Box } = $.ui.resolve(e)
    // The rows keep to the top, under the spinner; Clawd keeps its feet on the prompt's border.
    return (
      <Box flexDirection="row">
        <Box key="rows" flexDirection="column" flexGrow={1} flexShrink={1}>
          {stacked}
        </Box>
        <Box key="clawd-beside" flexDirection="column" justifyContent="flex-end" flexShrink={0}>
          {beside}
        </Box>
      </Box>
    )
  })
}
