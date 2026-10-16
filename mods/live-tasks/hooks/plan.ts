import type { Plan, Step, StepStatus } from '../types'

/** The arguments of the update_plan tool, as the desktop app's tool takes them. */
export type PlanInput = {
  items?: { content: string; status: StepStatus }[]
  advance?: boolean
  done?: number[]
  start?: number
}

export type PlanUpdate = { plan: Plan; text: string } | { error: string }

const STATUSES: readonly StepStatus[] = ['pending', 'in_progress', 'completed']

export function applyPlanInput(current: Plan | null, input: PlanInput): PlanUpdate {
  if (input.items !== undefined) {
    if (!Array.isArray(input.items) || input.items.length === 0) {
      return { error: '`items` must be a non-empty list of steps.' }
    }
    const steps: Step[] = input.items.map((item, i) => ({
      id: String(i + 1),
      content: String(item.content ?? '').trim() || `Step ${i + 1}`,
      status: STATUSES.includes(item.status) ? item.status : 'pending',
    }))
    const plan: Plan = { source: 'plan', steps }
    return { plan, text: `Plan shown (${steps.length} steps).` }
  }

  if (current === null || current.source !== 'plan') {
    return { error: 'No plan yet: send the whole list with `items` first.' }
  }

  const steps = current.steps.map(s => ({ ...s }))
  const count = steps.length
  const inRange = (n: number) => Number.isInteger(n) && n >= 1 && n <= count

  if (input.advance === true) {
    const at = steps.findIndex(s => s.status === 'in_progress')
    if (at !== -1) steps[at].status = 'completed'
    const after = steps.findIndex((s, i) => i > at && s.status === 'pending')
    const next = after !== -1 ? after : steps.findIndex(s => s.status === 'pending')
    if (next !== -1) steps[next].status = 'in_progress'
  }

  for (const n of input.done ?? []) {
    if (!inRange(n)) return { error: `\`done\` has ${n}: steps are numbered 1 to ${count}.` }
    steps[n - 1].status = 'completed'
  }

  if (input.start !== undefined) {
    if (!inRange(input.start)) {
      return { error: `\`start\` is ${input.start}: steps are numbered 1 to ${count}.` }
    }
    for (const s of steps) if (s.status === 'in_progress') s.status = 'pending'
    steps[input.start - 1].status = 'in_progress'
  }

  const plan: Plan = { source: 'plan', steps }
  return { plan, text: describe(plan) }
}

export function describe(plan: Plan): string {
  const count = plan.steps.length
  const at = plan.steps.findIndex(s => s.status === 'in_progress')
  if (at !== -1) return `Plan updated: step ${at + 1} of ${count} is in progress.`
  if (plan.steps.every(s => s.status === 'completed')) return `All ${count} steps done.`
  return `Plan updated: ${countDone(plan)} of ${count} steps done.`
}

export function countDone(plan: Plan): number {
  return plan.steps.filter(s => s.status === 'completed').length
}

export function isFinished(plan: Plan): boolean {
  return plan.steps.every(s => s.status === 'completed')
}

/** A list of this mod's own tool stays until it is finished; built-ins may then replace it. */
export function mayMirror(current: Plan | null): boolean {
  return current === null || current.source !== 'plan' || isFinished(current)
}

/**
 * Which steps fit in `rows` rows: everything when it fits, otherwise the
 * earliest finished steps fold into one "N more done" row.
 */
export function fit(steps: Step[], rows: number): { folded: number; shown: Step[] } {
  if (steps.length <= rows) return { folded: 0, shown: steps }
  const room = Math.max(1, rows - 1)
  let folded = 0
  const shown = [...steps]
  while (shown.length > room && shown[0]?.status === 'completed') {
    shown.shift()
    folded += 1
  }
  return { folded, shown: shown.slice(0, folded > 0 ? room : rows) }
}
