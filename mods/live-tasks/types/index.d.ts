export type StepStatus = 'pending' | 'in_progress' | 'completed'

export type Step = { id: string; content: string; status: StepStatus }

/** Where the list came from: this mod's own tool, or a mirrored built-in. */
export type PlanSource = 'plan' | 'todo' | 'task'

export type Plan = { source: PlanSource; steps: Step[] }

declare module 'claude-code' {
  interface PluginState {
    'live-tasks': { plan: Plan | null; isHidden: boolean }
  }
}
