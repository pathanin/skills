import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Plan, Step, StepStatus } from '../types'
import { applyPlanInput, countDone, fit, mayMirror } from './plan'
import type { PlanInput } from './plan'

const plan = atom({ plugin: 'live-tasks', key: 'plan' } as const, null)
const isHidden = atom({ plugin: 'live-tasks', key: 'isHidden' } as const, false)

const TOOL = 'mcp__live-tasks__update_plan'

const DESCRIPTION = `Keep the live task list the person sees above the prompt while you work. Every request that edits files or runs more than one command gets one; only a single-command answer or pure conversation does not.

Never spend a message on this tool alone: send it in the same message as another tool call (in parallel), so it costs no extra round trip.
- First call: with the very first tool call of the turn, even one that only reads or lists files: {"items": [...]}, the whole plan in order, short imperative phrases (at most ~7 words, no numbering), the step you are starting "in_progress", the rest "pending". If you must look around first, make "Look at how X is set up" step one and refine the list once you know.
- Next step: {"advance": true} alongside the call that begins it (completes the in_progress step, starts the next pending one). After the last step, send {"advance": true} once more with your final tool call so every step ends checked.
- Out of order: {"done": [2], "start": 4} (1-based).
- Plan changed, including right after the user interrupts or sends a new instruction mid-task: {"items": [...]} again, the new whole list, so the list never shows an abandoned plan.
Keep exactly one step in_progress while working and none when everything is done. Do not also write the plan as a numbered list in your message: the live list is the plan.`

const INPUT_SCHEMA = {
  type: 'object',
  properties: {
    items: {
      type: 'array',
      description: 'The whole plan, in order (1-12 steps); replaces the previous list.',
      minItems: 1,
      maxItems: 12,
      items: {
        type: 'object',
        properties: {
          content: { type: 'string' },
          status: { type: 'string', enum: ['pending', 'in_progress', 'completed'] },
        },
        required: ['content', 'status'],
      },
    },
    advance: { type: 'boolean' },
    done: { type: 'array', items: { type: 'number' } },
    start: { type: 'number' },
  },
}

const SECTION = {
  id: 'live-tasks:instructions',
  scope: 'session',
  text: `# Live task list
The person follows your progress on a live task list drawn above their prompt, not by reading your messages, so keeping it is part of doing the task. The tool ${TOOL} is that list: use it in place of TodoWrite, TaskCreate and TaskUpdate. For every request that involves editing files or running more than one command, the very first tool call of the turn (even one that only reads a file) goes out together with ${TOOL} carrying the whole plan; as each step finishes, {"advance": true} rides along with the call that starts the next step; if the plan changes or the person redirects you, send the whole list again. Only a single-command answer or pure conversation goes without one. Do not restate the plan as a list in your text.`,
} as const

const MARK: Record<StepStatus, string> = { completed: '✓', in_progress: '◼', pending: '○' }

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const surfaces = await $.session.surfaces()
    if (surfaces.includes('terminal')) {
      await $.tool.register({
        name: 'update_plan',
        description: DESCRIPTION,
        inputSchema: INPUT_SCHEMA,
        isDeferred: false,
      })
    }
    await $.command.register({
      name: 'live-tasks',
      description: 'Show, hide or clear the live task list.',
      argumentHint: '[show|hide|clear]',
    })
    return next(e)
  })

  on('session.end', async ($, e, next) => {
    if (e.reason === 'clear') await update($, plan, () => null)
    return next(e)
  })

  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    if (!e.surfaces.includes('terminal') || !e.tools.includes(TOOL)) return composed
    return { sections: [...composed.sections, SECTION] }
  })

  // The mod's own tool: the desktop app's update_plan, drawn in the terminal.
  on('tool.call', { tool: TOOL }, async ($, e) => {
    const { tool, tool_use_id, agentId, requestMeta, ...input } = e as typeof e & Record<string, unknown>
    if (agentId !== undefined) {
      return { result: 'The live task list belongs to the main conversation; a subagent does not update it.' }
    }
    const answer = applyPlanInput(await read($, plan), input as PlanInput)
    if ('error' in answer) return { result: answer.error, isError: true }
    await update($, plan, () => answer.plan)
    return { result: answer.text }
  })

  // The built-in task tools are mirrored while the mod's own list is not in charge.
  on('tool.call', { tool: 'TodoWrite' }, async ($, e, next) => {
    const ran = await next(e)
    if (e.agentId !== undefined || ran.deny !== undefined || ran.isError === true) return ran
    if (!mayMirror(await read($, plan))) return ran
    const steps: Step[] = e.todos.map((t, i) => ({ id: String(i + 1), content: t.content, status: t.status }))
    await update($, plan, () => (steps.length === 0 ? null : { source: 'todo', steps }))
    return ran
  }).catch(($, e, next) => next(e))

  on('tool.call', { tool: 'TaskCreate' }, async ($, e, next) => {
    const ran = await next(e)
    if (e.agentId !== undefined || ran.deny !== undefined || ran.isError === true) return ran
    const id = ran.result.task.id
    await update($, plan, current => {
      if (!mayMirror(current)) return current
      const kept = current?.source === 'task' ? current.steps : []
      return { source: 'task', steps: [...kept, { id, content: e.subject, status: 'pending' }] }
    })
    return ran
  }).catch(($, e, next) => next(e))

  on('tool.call', { tool: 'TaskUpdate' }, async ($, e, next) => {
    const ran = await next(e)
    if (e.agentId !== undefined || ran.deny !== undefined || ran.isError === true) return ran
    await update($, plan, current => {
      if (current?.source !== 'task') return current
      if (e.status === 'deleted') {
        const steps = current.steps.filter(s => s.id !== e.taskId)
        return steps.length === 0 ? null : { ...current, steps }
      }
      const steps = current.steps.map(s =>
        s.id !== e.taskId ? s : { ...s, content: e.subject ?? s.content, status: e.status ?? s.status },
      )
      return { ...current, steps }
    })
    return ran
  }).catch(($, e, next) => next(e))

  on('command.run', { command: 'live-tasks' }, async ($, e) => {
    const arg = e.args.trim().toLowerCase()
    if (arg === 'clear') {
      await update($, plan, () => null)
      return { text: 'Cleared the live task list.' }
    }
    const hide = arg === 'hide' ? true : arg === 'show' ? false : !(await read($, isHidden))
    await update($, isHidden, () => hide)
    return { text: hide ? 'Live task list hidden.' : 'Live task list shown.' }
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.surface !== 'terminal' || e.props.hasSurvey) return next(e)
    const current: Plan | null = await read($, plan)
    if (current === null || current.steps.length === 0 || (await read($, isHidden))) return next(e)

    const { Box, Text } = $.ui.resolve(e)
    const total = current.steps.length
    const done = countDone(current)
    const { folded, shown } = fit(current.steps, Math.max(2, e.props.maxRows - 1))

    return (
      <Box flexDirection="column">
        <Text key="head" wrap="truncate-end">
          <Text weight="bold">Tasks</Text>
          <Text dimColor>{`  ${done} of ${total} done`}</Text>
        </Text>
        {folded > 0 ? (
          <Text key="folded" dimColor wrap="truncate-end">
            <Text color="success">{'✓ '}</Text>
            {`${folded} more done`}
          </Text>
        ) : null}
        {shown.map(step => (
          <Text key={`step-${step.id}`} wrap="truncate-end">
            {step.status === 'completed' ? (
              <Text color="success">{`${MARK.completed} `}</Text>
            ) : step.status === 'in_progress' ? (
              <Text color="claude">{`${MARK.in_progress} `}</Text>
            ) : (
              <Text dimColor>{`${MARK.pending} `}</Text>
            )}
            {step.status === 'completed' ? (
              <Text dimColor strikethrough>{step.content}</Text>
            ) : step.status === 'in_progress' ? (
              <Text weight="bold">{step.content}</Text>
            ) : (
              <Text>{step.content}</Text>
            )}
          </Text>
        ))}
      </Box>
    )
  })
}
