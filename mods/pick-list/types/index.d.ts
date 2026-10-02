export type Option = { n: number; title: string }

declare module 'claude-code' {
  interface PluginState {
    'pick-list': { options: Option[]; picked: number[] }
  }
}
