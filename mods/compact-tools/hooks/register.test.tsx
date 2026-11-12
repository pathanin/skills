import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

const use = (tool: string, input: unknown, extra: Record<string, unknown> = {}) =>
  ({
    plugin: 'compact-tools',
    component: 'ToolUse',
    requestId: 't1',
    props: {
      tool_use_id: 't1',
      tool,
      input,
      isRunning: false,
      isErrored: false,
      isInterrupted: false,
      isExpanded: false,
      ...extra,
    },
  }) as const

const engine = (on: On) =>
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })

test('a Bash call draws one Ran line with the command', async ($, on) => {
  engine(on)
  const ui = await $.ui.mount({
    ...use('Bash', { command: 'ls   -la\nsecond line' }),
    surface: 'terminal',
  })
  const row = await ui.find({ type: 'Text', text: /Ran/ })
  expect(row?.text).toContain('Ran (ls -la)')
  expect(row?.text).not.toContain('second line')
  expect(await ui.find({ type: 'Text', text: /engine/ })).toBeUndefined()
  await ui.unmount()
})

test('an expanded call falls through to the engine', async ($, on) => {
  engine(on)
  const ui = await $.ui.mount({
    ...use('Bash', { command: 'ls' }, { isExpanded: true }),
    surface: 'terminal',
  })
  expect((await ui.find({ type: 'Text', text: /engine/ }))?.text).toBe('engine')
  expect(await ui.find({ type: 'Text', text: /Ran/ })).toBeUndefined()
  await ui.unmount()
})

test('an errored Edit shows failed with the error line', async ($, on) => {
  engine(on)
  const ui = await $.ui.mount({
    ...use(
      'Edit',
      { file_path: '/a/b/c.ts' },
      { isErrored: true, output: 'String not found\nmore' },
    ),
    surface: 'terminal',
  })
  const row = await ui.find({ type: 'Text', text: /Edited/ })
  expect(row?.text).toContain('Edited 1 file (c.ts)')
  expect(row?.text).toContain('failed: String not found')
  expect(row?.text).toContain('ctrl+o to expand')
  await ui.unmount()
})

test('a ToolResult draws nothing when not expanded', async ($, on) => {
  engine(on)
  const ui = await $.ui.mount({
    plugin: 'compact-tools',
    component: 'ToolResult',
    requestId: 't1',
    props: { tool_use_id: 't1', tool: 'Bash', output: { stdout: 'hi' }, isErrored: false, isExpanded: false },
    surface: 'terminal',
  })
  expect(await ui.find({ type: 'Text' })).toBeUndefined()
  await ui.unmount()
})

test('a calls-only group counts its calls', async ($, on) => {
  engine(on)
  const call = (tool: string) => ({ tool, input: {}, isRunning: false, isErrored: false, isInterrupted: false })
  const ui = await $.ui.mount({
    plugin: 'compact-tools',
    component: 'ToolGroup',
    props: {
      calls: [call('Read'), call('Read'), call('Grep')],
      isActive: false,
      isExpanded: false,
      isCallsOnly: true,
    },
    surface: 'terminal',
  })
  const row = await ui.find({ type: 'Text', text: /actions/ })
  expect(row?.text).toBe('… 3 actions (2 reads, 1 search) …')
  await ui.unmount()
})

test('another surface falls through to the engine', async ($, on) => {
  engine(on)
  const ui = await $.ui.mount({ ...use('Bash', { command: 'ls' }), surface: 'desktop' })
  expect((await ui.find({ type: 'Text', text: /engine/ }))?.text).toBe('engine')
  await ui.unmount()
})

const bashRow = (id: string, command: string, extra: Record<string, unknown> = {}) =>
  ({
    plugin: 'compact-tools',
    component: 'ToolUse',
    requestId: id,
    surface: 'terminal',
    props: {
      tool_use_id: id,
      tool: 'Bash',
      input: { command },
      isRunning: false,
      isErrored: false,
      isInterrupted: false,
      isExpanded: false,
      ...extra,
    },
  }) as const

const STEP = { turnId: 't', index: 0, model: 'opus', messageCount: 1 } as const
const STEP_RESULT = { turnId: 't', index: 0, answer: '', toolUses: [], stopReason: 'tool_use', usage: null } as const

async function drain(stream: AsyncGenerator<unknown, unknown>) {
  for (;;) if ((await stream.next()).done) return
}

test('a run of 3 Bash calls draws one merged line on its last row', async ($, on) => {
  engine(on)
  on('tool.call', () => ({ result: { stdout: '', stderr: '', interrupted: false } }))
  await $.tool.call({ tool: 'Bash', command: 'sed -n 1,12p a.ts', tool_use_id: 'b1' })
  await $.tool.call({ tool: 'Bash', command: 'npm test', tool_use_id: 'b2' })
  await $.tool.call({ tool: 'Bash', command: 'tail -8 log.txt', tool_use_id: 'b3' })

  for (const id of ['b1', 'b2']) {
    const ui = await $.ui.mount(bashRow(id, 'x'))
    expect(await ui.find({ type: 'Text' })).toBeUndefined()
    await ui.unmount()
  }
  const ui = await $.ui.mount(bashRow('b3', 'tail -8 log.txt'))
  const row = await ui.find({ type: 'Text', text: /Ran 3 commands/ })
  expect(row?.text).toContain('Ran 3 commands (+2 · sed -n 1,12p a.ts · tail -8 log.txt)')
  expect(row?.text).toContain('(ctrl+o to expand)')
  await ui.unmount()
})

test('assistant text breaks a run', async ($, on) => {
  engine(on)
  on('tool.call', () => ({ result: { stdout: '', stderr: '', interrupted: false } }))
  on('turn.step', async function* () {
    yield { kind: 'text', index: 0, text: 'Now the tests.' } as const
    return { ...STEP_RESULT, answer: 'Now the tests.' }
  })
  await $.tool.call({ tool: 'Bash', command: 'make', tool_use_id: 'c1' })
  await drain($.turn.step(STEP))
  await $.tool.call({ tool: 'Bash', command: 'npm test', tool_use_id: 'c2' })

  const first = await $.ui.mount(bashRow('c1', 'make'))
  expect((await first.find({ type: 'Text', text: /Ran/ }))?.text).toContain('Ran (make)')
  await first.unmount()
  const second = await $.ui.mount(bashRow('c2', 'npm test'))
  const row = await second.find({ type: 'Text', text: /Ran/ })
  expect(row?.text).toContain('Ran (npm test)')
  expect(row?.text).not.toContain('commands')
  await second.unmount()
})

test('a single call draws as before', async ($, on) => {
  engine(on)
  on('tool.call', () => ({ result: { stdout: '', stderr: '', interrupted: false } }))
  await $.tool.call({ tool: 'Bash', command: 'make', tool_use_id: 's1' })
  const ui = await $.ui.mount(bashRow('s1', 'make'))
  const row = await ui.find({ type: 'Text', text: /Ran/ })
  expect(row?.text).toBe('● Ran (make)')
  await ui.unmount()
})

test('a thought line sits above the row that followed the thinking', async ($, on) => {
  engine(on)
  const clock = mock.clock(on, { now: 1000 })
  on('turn.step', async function* () {
    yield { kind: 'thinking', index: 0, text: 'All 520 tests passed, so the next step is lint.\nMore.' } as const
    yield { kind: 'tool', index: 1, id: 'th1', name: 'Bash' } as const
    return STEP_RESULT
  })
  const stream = $.turn.step(STEP)
  await stream.next()
  await clock.advance(23200)
  await drain(stream)

  const ui = await $.ui.mount(bashRow('th1', 'npm run lint'))
  const thought = await ui.find({ type: 'Text', text: /Thought/ })
  expect(thought?.text).toBe('○ Thought for 23.2s (All 520 tests passed, so the next step is lint.)')
  expect((await ui.find({ type: 'Text', text: /Ran/ }))?.text).toContain('Ran (npm run lint)')
  await ui.unmount()
})

test('an errored call in a stored run turns the bullet red', async ($, on) => {
  engine(on)
  // A run an earlier load stored, before this reload.
  on('state.get', (_, e, next) =>
    e.key === 'runs'
      ? {
          value: {
            value: {
              runs: {
                r1: [
                  { id: 'e1', tool: 'Bash', kind: 'command', detail: 'make', status: 'error', error: 'make: *** failed' },
                  { id: 'e2', tool: 'Bash', kind: 'command', detail: 'ls', status: 'done' },
                ],
              },
              of: { e1: 'r1', e2: 'r1' },
              open: 'r1',
              seq: 1,
              order: ['r1'],
            },
            version: 3,
          },
        }
      : next(e),
  )
  const ui = await $.ui.mount(bashRow('e2', 'ls'))
  const row = await ui.find({ type: 'Text', text: /Ran 2 commands/ })
  expect(row?.text).toContain('failed: make: *** failed')
  const bullet = await ui.find({ type: 'Text', text: /^●$/ })
  expect(bullet?.props?.color).toBe('#d47766')
  await ui.unmount()
})

test('an expanded row in a run passes through', async ($, on) => {
  engine(on)
  on('tool.call', () => ({ result: { stdout: '', stderr: '', interrupted: false } }))
  await $.tool.call({ tool: 'Bash', command: 'a', tool_use_id: 'x1' })
  await $.tool.call({ tool: 'Bash', command: 'b', tool_use_id: 'x2' })
  const ui = await $.ui.mount(bashRow('x1', 'a', { isExpanded: true }))
  expect((await ui.find({ type: 'Text', text: /engine/ }))?.text).toBe('engine')
  await ui.unmount()
})

test('reply text gets a blank line above and below it', async ($, on) => {
  engine(on)
  const ui = await $.ui.mount({
    plugin: 'compact-tools',
    component: 'AssistantMessage',
    props: { text: 'Done.', isFirstOfReply: true },
    surface: 'terminal',
  })
  const drawn = (await ui.drawn()) as { children: Array<{ type: string; children?: unknown[] }> }
  expect(drawn.children[0]).toMatchObject({ type: 'Text', children: [' '] })
  expect(drawn.children.at(-1)).toMatchObject({ type: 'Text', children: [' '] })
  expect(await ui.find({ type: 'Text', text: /engine/ })).toBeDefined()
  await ui.unmount()
})

test('a prompt row hides the system-reminder a mod appended', async ($, on) => {
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>{`row:${(e.props as { text: string }).text}`}</Text>
  })
  const props = {
    text: 'try 50%\n<system-reminder>The live task list was left unfinished.</system-reminder>',
    origin: { kind: 'composer' },
    isExpanded: false,
  }
  const ui = await $.ui.mount({ plugin: 'compact-tools', component: 'UserMessage', props, surface: 'terminal' } as never)
  expect(await ui.find({ type: 'Text', text: 'row:try 50%' })).toBeDefined()
  await ui.unmount()
  const full = await $.ui.mount({
    plugin: 'compact-tools',
    component: 'UserMessage',
    props: { ...props, isExpanded: true },
    surface: 'terminal',
  } as never)
  expect(await full.find({ type: 'Text', text: /system-reminder/ })).toBeDefined()
  await full.unmount()
})

test('a prompt block that is only a system-reminder draws no row', async ($, on) => {
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>{`row:${(e.props as { text: string }).text}`}</Text>
  })
  const props = {
    text: '<system-reminder>The live task list was left unfinished.</system-reminder>',
    origin: { kind: 'composer' },
    isExpanded: false,
  }
  const ui = await $.ui.mount({ plugin: 'compact-tools', component: 'UserMessage', props, surface: 'terminal' } as never)
  expect(await ui.find({ type: 'Text', text: /row:/ })).toBeUndefined()
  await ui.unmount()
})
