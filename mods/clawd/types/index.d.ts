/** Which colour a stretch of the drawing takes: Clawd's own, its side in shade, the laptop's
 * grey, or a key lit as it is pressed. */
export type Tone = 'clawd' | 'shade' | 'laptop' | 'key'

/** A stretch of cells in one tone. Solid ones are drawn the other way round: the tone as the
 * cells' background, their empty quadrants over it in the terminal's own background. */
export type Run = { text: string; tone: Tone; isSolid: boolean }

/** Clawd's drawing: one row of runs per terminal row, every row the same width. */
export type Sprite = readonly (readonly Run[])[]

declare module 'claude-code' {
  interface PluginState {
    clawd: { sprite: Sprite | null; isHidden: boolean }
  }
}
