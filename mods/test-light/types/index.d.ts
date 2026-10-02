export type Run = {
  ok: boolean
  passed?: number
  failed?: number
  at: number
  edited: string[]
}

declare module 'claude-code' {
  interface PluginState {
    'test-light': { last: Run | null; minute: number }
  }
}
