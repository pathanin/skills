/** Clawd's drawing: rows of pixels, two of them to a terminal cell each way. '.' is empty;
 * every other letter is a colour (see `COLORS` in hooks/sprite.ts). */
export type Grid = readonly string[]

declare module 'claude-code' {
  interface PluginState {
    clawd: { sprite: Grid | null; isHidden: boolean; isImage: boolean }
  }
}
