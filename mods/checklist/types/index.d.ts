export type Status = 'pending' | 'in_progress' | 'done'
export type Item = { text: string; status: Status }

declare module 'claude-code' {
  interface PluginState {
    checklist: { items: Item[] }
  }
}
