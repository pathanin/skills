export type RunCall = {
  id: string
  tool: string
  kind: string
  detail?: string
  status: 'running' | 'done' | 'error'
  error?: string
}

export type Runs = {
  /** Each run's calls, in call order, by run id. */
  runs: Record<string, RunCall[]>
  /** Which run a call belongs to, by tool_use_id. */
  of: Record<string, string>
  /** The run the next same-kind call joins; null after a break. */
  open: string | null
  seq: number
  /** Run ids oldest first, for the cap. */
  order: string[]
}

export type Thought = { seconds: number; summary?: string }

export type Thoughts = {
  /** By the tool_use_id of the first call after the thinking. */
  items: Record<string, Thought>
  order: string[]
}

declare module 'claude-code' {
  interface PluginState {
    'compact-tools': { runs: Runs; thoughts: Thoughts }
  }
}
