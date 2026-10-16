/** Clawd's drawing: one string per terminal row, all the same width. */
export type Sprite = readonly string[]

declare module 'claude-code' {
  interface PluginState {
    clawd: { sprite: Sprite | null; isHidden: boolean }
  }
}
