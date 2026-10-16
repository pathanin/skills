/** Which colour a stretch of the drawing takes: Clawd's own, its side in shade, the laptop's
 * grey, or a key lit as it is pressed. */
export type Tone = 'clawd' | 'shade' | 'laptop' | 'key'

export type Run = { text: string; tone: Tone }

/** Clawd's drawing: one row of runs per terminal row, every row the same width. */
export type Sprite = readonly (readonly Run[])[]

declare module 'claude-code' {
  interface PluginState {
    clawd: { sprite: Sprite | null; isHidden: boolean }
  }
}
