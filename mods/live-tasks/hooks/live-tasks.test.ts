import { describe, expect, test } from 'claude-code/testing'
import type { RenderPropsOf } from 'claude-code'

const TOOL = 'mcp__live-tasks__update_plan'

const BAND = {
  plugin: 'live-tasks',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isWorking: true,
    maxRows: 20,
    bodyColumns: 80,
    scroll: { bodyRows: 19, offset: 0 },
  } as unknown as RenderPropsOf['AbovePrompt'],
} as const

const ITEMS = [
  { content: 'Look at the code', status: 'in_progress' },
  { content: 'Write the fix', status: 'pending' },
  { content: 'Run the tests', status: 'pending' },
]

type Node = { children?: unknown[] } | string

function flatten(node: Node): string {
  if (typeof node === 'string') return node
  return (node.children ?? []).map(c => flatten(c as Node)).join('')
}

/** The band's rows as the terminal draws them; empty when the mod draws nothing. */
async function rows($: any, surface: 'terminal' | 'desktop' = 'terminal'): Promise<string[]> {
  const ui = await $.ui.mount({ ...BAND, surface })
  const drawn = (await ui.drawn()) as { type?: string; children?: unknown[] } | null
  await ui.unmount()
  if (drawn === null || drawn === undefined || drawn.type !== 'Box') return []
  return (drawn.children ?? []).map(c => flatten(c as Node))
}

// Stands for the engine's own band when the mod passes: a lone Text, never the mod's Box.
const engineBand = (on: any) =>
  on('ui.render', { component: 'AbovePrompt' }, ($: any, e: any) => {
    const { Text } = $.ui.resolve(e)
    return h(Text, null, 'engine')
  })

describe('update_plan', () => {
  test('draws the plan and moves through it like the desktop list', async ($, on) => {
    const first = await $.tool.call({ tool: TOOL, items: ITEMS })
    expect(first.result).toBe('Plan shown (3 steps).')
    expect(await rows($)).toEqual(['Tasks  0 of 3 done', '◼ Look at the code', '○ Write the fix', '○ Run the tests'])

    const second = await $.tool.call({ tool: TOOL, advance: true })
    expect(second.result).toBe('Plan updated: step 2 of 3 is in progress.')
    expect(await rows($)).toEqual(['Tasks  1 of 3 done', '✓ Look at the code', '◼ Write the fix', '○ Run the tests'])

    await $.tool.call({ tool: TOOL, done: [2], start: 3 })
    const last = await $.tool.call({ tool: TOOL, advance: true })
    expect(last.result).toBe('All 3 steps done.')
    expect(await rows($)).toEqual(['Tasks  3 of 3 done', '✓ Look at the code', '✓ Write the fix', '✓ Run the tests'])
  })

  test('refuses an update with no plan, and out-of-range steps', async $ => {
    const none = await $.tool.call({ tool: TOOL, advance: true })
    expect(none.isError).toBe(true)
    await $.tool.call({ tool: TOOL, items: ITEMS })
    const bad = await $.tool.call({ tool: TOOL, start: 9 })
    expect(bad.isError).toBe(true)
  })

  test('draws nothing of its own outside the terminal', async ($, on) => {
    engineBand(on)
    await $.tool.call({ tool: TOOL, items: ITEMS })
    expect(await rows($, 'desktop')).toEqual([])
    expect((await rows($, 'terminal'))[0]).toBe('Tasks  0 of 3 done')
  })
})

describe('a new request', () => {
  // Stands for the engine's own start of a turn.
  const engineTurn = (on: any) => on('turn.start', ($: any, e: any) => e)

  const finish = async ($: any) => {
    await $.tool.call({ tool: TOOL, items: ITEMS })
    await $.tool.call({ tool: TOOL, done: [1, 2, 3] })
  }

  test('clears a finished list when the next prompt starts a turn', async ($, on) => {
    engineBand(on)
    engineTurn(on)
    await finish($)
    expect((await rows($))[0]).toBe('Tasks  3 of 3 done')
    await $.turn.start({ text: 'also make it the default', turnId: 't2' })
    expect(await rows($)).toEqual([])
    const next = await $.tool.call({ tool: TOOL, items: [{ content: 'New step', status: 'in_progress' }] })
    expect(next.result).toBe('Plan shown (1 steps).')
    expect(await rows($)).toEqual(['Tasks  0 of 1 done', '◼ New step'])
  })

  test('keeps an unfinished list, and ignores subagent and continuation turns', async ($, on) => {
    engineTurn(on)
    await $.tool.call({ tool: TOOL, items: ITEMS })
    await $.turn.start({ text: 'keep going', turnId: 't2' })
    expect((await rows($))[0]).toBe('Tasks  0 of 3 done')

    await $.tool.call({ tool: TOOL, done: [1, 2, 3] })
    await $.turn.start({ text: 'sub prompt', turnId: 't3', agentId: 'sub-1' })
    await $.turn.start({ text: '', turnId: 't4' })
    expect((await rows($))[0]).toBe('Tasks  3 of 3 done')
  })
})

describe('built-in task tools', () => {
  test('TodoWrite is mirrored while the mod has no list of its own', async ($, on) => {
    on('tool.call', { tool: 'TodoWrite' }, () => ({ result: { oldTodos: [], newTodos: [] } }) as never)
    await $.tool.call({
      tool: 'TodoWrite',
      todos: [
        { content: 'One', status: 'completed', activeForm: 'Doing one' },
        { content: 'Two', status: 'in_progress', activeForm: 'Doing two' },
      ],
    })
    expect(await rows($)).toEqual(['Tasks  1 of 2 done', '✓ One', '◼ Two'])
  })

  test('an unfinished update_plan list is not replaced by TodoWrite', async ($, on) => {
    on('tool.call', { tool: 'TodoWrite' }, () => ({ result: { oldTodos: [], newTodos: [] } }) as never)
    await $.tool.call({ tool: TOOL, items: ITEMS })
    await $.tool.call({ tool: 'TodoWrite', todos: [{ content: 'Other', status: 'pending', activeForm: 'Other' }] })
    expect((await rows($))[1]).toBe('◼ Look at the code')
  })

  test('subagent calls do not touch the list', async ($, on) => {
    engineBand(on)
    on('tool.call', { tool: 'TodoWrite' }, () => ({ result: { oldTodos: [], newTodos: [] } }) as never)
    await $.tool.call({ tool: 'TodoWrite', agentId: 'sub-1', todos: [{ content: 'Sub', status: 'pending', activeForm: 'Sub' }] } as never)
    expect(await rows($)).toEqual([])
  })
})

describe('transcript rows', () => {
  const row = (isErrored: boolean) =>
    ({
      plugin: 'live-tasks',
      surface: 'terminal',
      component: 'ToolUse',
      props: { tool_use_id: 'tu1', tool: TOOL, input: {}, isRunning: false, isErrored, isInterrupted: false },
    }) as const

  test("update_plan's row draws nothing in the terminal, like the desktop app", async ($, on) => {
    engineRow(on)
    const ui = await $.ui.mount(row(false) as never)
    expect(flatten((await ui.drawn()) as Node)).toBe('')
    await ui.unmount()
  })

  test('a failed update_plan call keeps its row', async ($, on) => {
    engineRow(on)
    const ui = await $.ui.mount(row(true) as never)
    expect(flatten((await ui.drawn()) as Node)).toBe('engine row')
    await ui.unmount()
  })
})

// Stands for the engine's own tool row.
const engineRow = (on: any) =>
  on('ui.render', { component: 'ToolUse' }, ($: any, e: any) => {
    const { Text } = $.ui.resolve(e)
    return h(Text, null, 'engine row')
  })
