import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Item } from '../types'
import { summary } from './summary'

const PANE = 'checklist'
const TOOL = 'mcp__checklist__checklist'
const items = atom({ plugin: 'checklist', key: 'items' } as const, [])

const DESCRIPTION = `Keep a visible checklist of the work for this request; the user watches it live.
For any task with 3+ steps: call this before starting with every step as "pending", the first one "in_progress".
Call it again the moment a step finishes: mark it "done" and the next "in_progress". Exactly one step is "in_progress" while work remains.
Add steps you discover as you go. Each call replaces the whole list, so always send every item.
Keep working until every item is "done" (or remove an item if the user drops it). Skip this tool for one-step requests.`

const MARK = { pending: '☐', in_progress: '▶', done: '☑' } as const

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.tool.register({
      name: 'checklist',
      description: DESCRIPTION,
      inputSchema: {
        type: 'object',
        properties: {
          items: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                text: { type: 'string', description: 'The step, short and imperative' },
                status: { type: 'string', enum: ['pending', 'in_progress', 'done'] },
              },
              required: ['text', 'status'],
            },
          },
        },
        required: ['items'],
      },
    })
    await $.command.register({ name: 'checklist', description: "Show Claude's work checklist" })
    return next(e)
  })

  // Keep the schema in the prompt so Claude reaches for it unprompted, not behind ToolSearch.
  on('tool.describe', { tool: TOOL }, async ($, e, next) => ({ ...(await next(e)), isDeferred: false }))

  on('command.run', { command: 'checklist' }, async $ => {
    await $.ui.open({ id: PANE, title: 'Checklist' })
    return { text: 'Checklist opened.' }
  })

  on('tool.call', { tool: TOOL }, async ($, e) => {
    // ponytail: main loop only; a subagent's checklist would overwrite the user's view.
    if (e.agentId) return { result: 'Checklist is shown for the main conversation only; skip it in subagents.' }
    const list = ((e as unknown as { items?: Item[] }).items ?? []).map(i => ({ text: String(i.text), status: i.status }))
    const wasEmpty = !(await read($, items)).length
    await update($, items, () => list)
    const done = list.filter(i => i.status === 'done').length
    $.ui.status(list.length ? `☑ ${done}/${list.length}` : undefined)
    if (wasEmpty && list.length) void $.ui.open({ id: PANE, title: 'Checklist' })
    return { result: summary(list) }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const list = await read($, items)
    if (!list.length) return <Text dimColor>No checklist yet.</Text>

    const done = list.filter(i => i.status === 'done').length
    return (
      <Box flexDirection="column">
        <Text bold>{done === list.length ? 'All done' : 'Progress'} {done}/{list.length}</Text>
        {list.map((item, n) => (
          <Text dimColor={item.status === 'done'} bold={item.status === 'in_progress'}>
            {MARK[item.status] ?? '☐'} {item.text}
          </Text>
        ))}
      </Box>
    )
  })
}
