import { atom, read, update } from 'claude-code'
import type { Elements, Register } from 'claude-code'

import type { RunCall, Runs, Thought, Thoughts } from '../types'

// Muted tones close to Antigravity's palette, not the terminal's bright ANSI ones.
const MUTED_YELLOW = '#d1bc6f'
const MUTED_GREEN = '#86b36b'
const MUTED_RED = '#d47766'

const PASS_THROUGH = new Set(['AskUserQuestion', 'ExitPlanMode', 'EnterPlanMode'])
const EXPAND_HINT = new Set(['Edit', 'MultiEdit', 'NotebookEdit', 'Write'])

function field(input: unknown, ...keys: string[]): string | undefined {
  if (input === null || typeof input !== 'object') return undefined
  for (const key of keys) {
    const value = (input as Record<string, unknown>)[key]
    if (typeof value === 'string' && value.trim() !== '') return value
  }
  return undefined
}

function oneLine(text: string): string {
  const first = text.split('\n').find(line => line.trim() !== '') ?? ''
  return first.replace(/\s+/g, ' ').trim()
}

function basename(path: string | undefined): string | undefined {
  if (path === undefined) return undefined
  const parts = path.split(/[\\/]/).filter(Boolean)
  return parts[parts.length - 1] ?? path
}

export function describe(tool: string, input: unknown): { verb: string; detail?: string } {
  switch (tool) {
    case 'Bash': {
      const command = field(input, 'command')
      return { verb: 'Ran', detail: command === undefined ? undefined : oneLine(command) }
    }
    case 'Edit':
    case 'MultiEdit':
    case 'NotebookEdit':
      return { verb: 'Edited 1 file', detail: basename(field(input, 'file_path', 'notebook_path')) }
    case 'Write':
      return { verb: 'Wrote 1 file', detail: basename(field(input, 'file_path')) }
    case 'Read':
      return { verb: 'Read 1 file', detail: basename(field(input, 'file_path')) }
    case 'Grep':
    case 'Glob':
      return { verb: 'Searched', detail: field(input, 'pattern') }
    case 'WebFetch':
      return { verb: 'Fetched', detail: field(input, 'url') }
    case 'WebSearch':
      return { verb: 'Searched web', detail: field(input, 'query') }
    case 'Agent':
    case 'Task':
      return { verb: 'Ran agent', detail: field(input, 'description') }
    case 'Skill':
      return { verb: 'Used skill', detail: field(input, 'skill') }
  }
  const mcp = /^mcp__(.+?)__(.+)$/.exec(tool)
  if (mcp) return { verb: `Used ${mcp[2]}`, detail: mcp[1] }
  return { verb: `Used ${tool}` }
}

function errorLine(output: unknown): string | undefined {
  if (typeof output === 'string') return oneLine(output) || undefined
  const text = field(output, 'text', 'error')
  return text === undefined ? undefined : oneLine(text) || undefined
}

const KINDS: Record<string, [string, string]> = {
  read: ['read', 'reads'],
  search: ['search', 'searches'],
  command: ['command', 'commands'],
  listing: ['listing', 'listings'],
  other: ['other', 'other'],
}

function kindOf(tool: string): string {
  if (tool === 'Read') return 'read'
  if (tool === 'Grep' || tool === 'Glob') return 'search'
  if (tool === 'Bash') return 'command'
  if (tool === 'LS' || tool === 'List' || /^ls$/i.test(tool)) return 'listing'
  return 'other'
}

export function summarize(tools: readonly string[]): string {
  const counts = new Map<string, number>()
  for (const tool of tools) {
    const kind = kindOf(tool)
    counts.set(kind, (counts.get(kind) ?? 0) + 1)
  }
  const parts = Object.keys(KINDS)
    .filter(kind => (counts.get(kind) ?? 0) > 0)
    .map(kind => {
      const n = counts.get(kind) ?? 0
      const [one, many] = KINDS[kind] ?? [kind, kind]
      return `${n} ${n === 1 ? one : many}`
    })
  const total = tools.length
  return `${total} ${total === 1 ? 'action' : 'actions'}${parts.length ? ` (${parts.join(', ')})` : ''}`
}

const RUNS_CAP = 200
const THOUGHTS_CAP = 200

const runsAtom = atom({ plugin: 'compact-tools', key: 'runs' } as const, {
  runs: {},
  of: {},
  open: null,
  seq: 0,
  order: [],
} as Runs)
const thoughtsAtom = atom({ plugin: 'compact-tools', key: 'thoughts' } as const, {
  items: {},
  order: [],
} as Thoughts)

/** The kind a call merges by; null for calls that never merge (and break a run). */
export function runKind(tool: string): string | null {
  if (tool === 'Bash') return 'command'
  if (tool === 'Edit' || tool === 'Write' || tool === 'MultiEdit' || tool === 'NotebookEdit') return 'edit'
  // Reads and searches fold into the engine's own ToolGroup; interactive tools stay full.
  if (tool === 'Read' || tool === 'Grep' || tool === 'Glob' || tool === 'LS' || PASS_THROUGH.has(tool)) return null
  return `tool:${tool}`
}

function callDetail(tool: string, input: unknown): string | undefined {
  if (tool === 'Bash') {
    const command = field(input, 'command')
    return command === undefined ? undefined : oneLine(command)
  }
  if (runKind(tool) === 'edit') return basename(field(input, 'file_path', 'notebook_path'))
  return undefined
}

function shortName(tool: string): string {
  return /^mcp__.+?__(.+)$/.exec(tool)?.[1] ?? tool
}

function clip(text: string, max = 30): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text
}

export function mergedLine(calls: readonly RunCall[]): { verb: string; detail?: string } {
  const n = calls.length
  const first = calls[0]
  const last = calls[n - 1]
  if (first === undefined || last === undefined) return { verb: 'Used 0 tools' }
  if (first.kind === 'command') {
    const parts = [`+${n - 1}`]
    if (first.detail !== undefined) parts.push(clip(first.detail))
    if (last.detail !== undefined) parts.push(clip(last.detail))
    return { verb: `Ran ${n} commands`, detail: parts.join(' · ') }
  }
  if (first.kind === 'edit') {
    const names = [...new Set(calls.map(c => c.detail).filter((d): d is string => d !== undefined))]
    const count = names.length > 0 ? names.length : n
    return { verb: `Edited ${count} ${count === 1 ? 'file' : 'files'}`, detail: names.length ? names.join(', ') : undefined }
  }
  return { verb: `Used ${n} tools`, detail: `${shortName(first.tool)} ×${n}` }
}

function capRuns(r: Runs): Runs {
  if (r.order.length <= RUNS_CAP) return r
  const drop = r.order.slice(0, r.order.length - RUNS_CAP)
  const runs = { ...r.runs }
  const of = { ...r.of }
  for (const id of drop) {
    for (const call of runs[id] ?? []) delete of[call.id]
    delete runs[id]
  }
  return { ...r, runs, of, order: r.order.slice(-RUNS_CAP), open: r.open !== null && drop.includes(r.open) ? null : r.open }
}

export function addCall(r: Runs, call: RunCall, breaksBefore: boolean): Runs {
  const open = breaksBefore ? null : r.open
  const current = open === null ? undefined : r.runs[open]
  if (open !== null && current !== undefined && current[0]?.kind === call.kind) {
    return { ...r, runs: { ...r.runs, [open]: [...current, call] }, of: { ...r.of, [call.id]: open } }
  }
  const id = `r${r.seq + 1}`
  return capRuns({
    runs: { ...r.runs, [id]: [call] },
    of: { ...r.of, [call.id]: id },
    open: id,
    seq: r.seq + 1,
    order: [...r.order, id],
  })
}

/** Takes a call out of its run, splitting the run there (a read-only Bash the engine may fold). */
export function detachCall(r: Runs, callId: string): Runs {
  const runId = r.of[callId]
  const calls = runId === undefined ? undefined : r.runs[runId]
  if (runId === undefined || calls === undefined) return r
  const at = calls.findIndex(c => c.id === callId)
  const before = calls.slice(0, at)
  const after = calls.slice(at + 1)
  const runs = { ...r.runs }
  const of = { ...r.of }
  delete of[callId]
  let { seq, open, order } = r
  if (before.length > 0) runs[runId] = before
  else {
    delete runs[runId]
    order = order.filter(id => id !== runId)
  }
  let afterId: string | null = null
  if (after.length > 0) {
    seq += 1
    afterId = `r${seq}`
    runs[afterId] = after
    for (const c of after) of[c.id] = afterId
    order = [...order, afterId]
  }
  if (open === runId) open = afterId
  return capRuns({ runs, of, open, seq, order })
}

function setStatus(r: Runs, callId: string, status: RunCall['status'], error?: string): Runs {
  const runId = r.of[callId]
  const calls = runId === undefined ? undefined : r.runs[runId]
  if (runId === undefined || calls === undefined) return r
  return {
    ...r,
    runs: { ...r.runs, [runId]: calls.map(c => (c.id === callId ? { ...c, status, error } : c)) },
  }
}

export function thinkingSummary(text: string): string | undefined {
  const flat = text.replace(/\*\*/g, '').replace(/\s+/g, ' ').trim()
  if (flat === '') return undefined
  const firstLine = text.split('\n').map(l => l.replace(/\*\*/g, '').trim()).find(l => l !== '') ?? flat
  const sentence = /^(.+?[.!?])(\s|$)/.exec(flat)?.[1] ?? flat
  return (sentence.length <= firstLine.length ? sentence : firstLine).replace(/\s+/g, ' ')
}

function addThought(t: Thoughts, id: string, thought: Thought): Thoughts {
  const order = [...t.order.filter(k => k !== id), id]
  const items = { ...t.items, [id]: thought }
  while (order.length > THOUGHTS_CAP) {
    const old = order.shift()
    if (old !== undefined) delete items[old]
  }
  return { items, order }
}

function thoughtLine(Text: Elements['terminal']['Text'], thought: Thought) {
  return (
    <Text dimColor wrap="truncate-end">
      {`○ Thought for ${formatSeconds(thought.seconds)}`}
      {thought.summary !== undefined ? ` (${thought.summary})` : ''}
    </Text>
  )
}

function formatSeconds(seconds: number): string {
  return `${seconds < 10 ? seconds.toFixed(1) : seconds.toFixed(1).replace(/\.0$/, '')}s`
}

export const register: Register = on => {
  on('prompt.submit', async ($, e, next) => {
    await update($, runsAtom, r => ({ ...r, open: null }))
    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    if (e.agentId !== undefined) return next(e)
    const kind = runKind(e.tool)
    const id = e.tool_use_id
    if (kind === null) {
      await update($, runsAtom, r => ({ ...r, open: null }))
      return next(e)
    }
    const thoughts = await read($, thoughtsAtom)
    const call: RunCall = { id, tool: e.tool, kind, detail: callDetail(e.tool, e), status: 'running' }
    await update($, runsAtom, r => addCall(r, call, thoughts.items[id] !== undefined))
    const result = await next(e)
    if (result.isError === true || result.deny !== undefined) {
      const text = result.deny ?? result.text ?? (typeof result.result === 'string' ? result.result : undefined)
      await update($, runsAtom, r => setStatus(r, id, 'error', text === undefined ? undefined : oneLine(text) || undefined))
    } else if (e.tool === 'Bash' && result.isReadOnly === true) {
      // The engine may fold a read-only command into its ToolGroup, where no ToolUse row of
      // ours would draw the run's merged line; keep it out of runs.
      await update($, runsAtom, r => detachCall(r, id))
    } else {
      await update($, runsAtom, r => setStatus(r, id, 'done'))
    }
    return result
  })

  on('turn.step', async function* ($, e, next) {
    const stream = next(e)
    if (e.agentId !== undefined) return yield* stream
    let startedAt: number | null = null
    let endedAt: number | null = null
    let text = ''
    for await (const chunk of stream) {
      if (chunk.kind === 'thinking') {
        if (startedAt === null || endedAt !== null) {
          if (startedAt === null) startedAt = await $.clock.now()
          endedAt = null
        }
        text += chunk.text
      } else if (startedAt !== null && endedAt === null) {
        endedAt = await $.clock.now()
      }
      if (chunk.kind === 'text' && chunk.text.trim() !== '') {
        startedAt = null
        endedAt = null
        text = ''
        await update($, runsAtom, r => (r.open === null ? r : { ...r, open: null }))
      } else if (chunk.kind === 'tool' && startedAt !== null) {
        const end = endedAt ?? (await $.clock.now())
        const thought: Thought = { seconds: Math.round((end - startedAt) / 100) / 10 }
        const summary = thinkingSummary(text)
        if (summary !== undefined) thought.summary = summary
        await update($, thoughtsAtom, t => addThought(t, chunk.id, thought))
        startedAt = null
        endedAt = null
        text = ''
      }
      yield chunk
    }
    return await stream.result
  })

  on('ui.render', { component: 'ToolUse' }, async ($, e, next) => {
    if (e.surface !== 'terminal' || e.props.isExpanded === true || PASS_THROUGH.has(e.props.tool)) {
      return next(e)
    }
    const { Box, Text } = $.ui.resolve(e)
    const { tool, input, isRunning, isErrored, isInterrupted, output, tool_use_id } = e.props
    const runs = await read($, runsAtom)
    const thoughts = await read($, thoughtsAtom)
    const runId = runs.of[tool_use_id]
    const run = runId === undefined ? undefined : runs.runs[runId]
    const isMerged = run !== undefined && run.length > 1

    if (isMerged && run[run.length - 1]?.id !== tool_use_id) return <Box />

    let verb: string
    let detail: string | undefined
    let color: string | undefined
    let failure: string | undefined
    let failed = false
    let interrupted = false
    let hint = EXPAND_HINT.has(tool)
    if (isMerged) {
      ;({ verb, detail } = mergedLine(run))
      const errored = run.find(c => c.status === 'error')
      failed = errored !== undefined || isErrored
      failure = errored?.error ?? (isErrored ? errorLine(output) : undefined)
      color = failed ? MUTED_RED : run.some(c => c.status === 'running') || isRunning ? MUTED_YELLOW : MUTED_GREEN
      hint = true
    } else {
      ;({ verb, detail } = describe(tool, input))
      interrupted = isInterrupted
      failed = isErrored && !isInterrupted
      failure = failed ? errorLine(output) : undefined
      color = isInterrupted ? undefined : isErrored ? MUTED_RED : isRunning ? MUTED_YELLOW : MUTED_GREEN
    }
    const thought = thoughts.items[isMerged ? (run[0]?.id ?? tool_use_id) : tool_use_id]

    const row = (
      <Text wrap="truncate-end">
        {color === undefined ? <Text dimColor>●</Text> : <Text color={color}>●</Text>}
        {' '}
        <Text bold color={MUTED_YELLOW}>{verb}</Text>
        {detail !== undefined ? <Text dimColor>{` (${detail})`}</Text> : null}
        {failed ? (
          <Text color={MUTED_RED}>{failure !== undefined ? ` — failed: ${failure}` : ' — failed'}</Text>
        ) : null}
        {interrupted ? <Text dimColor> — interrupted</Text> : null}
        {hint ? <Text dimColor> (ctrl+o to expand)</Text> : null}
      </Text>
    )
    if (thought === undefined) return <Box>{row}</Box>
    return (
      <Box flexDirection="column">
        {thoughtLine(Text, thought)}
        {row}
      </Box>
    )
  })

  on('ui.render', { component: 'ToolResult' }, ($, e, next) => {
    if (e.surface !== 'terminal' || e.props.isExpanded === true || PASS_THROUGH.has(e.props.tool)) {
      return next(e)
    }
    const { Box } = $.ui.resolve(e)
    return <Box />
  })

  on('ui.render', { component: 'ToolGroup' }, async ($, e, next) => {
    if (e.surface !== 'terminal' || e.props.isExpanded) return next(e)
    const { Box, Text } = $.ui.resolve(e)
    const thoughts = await read($, thoughtsAtom)
    const firstId = e.props.calls[0]?.tool_use_id
    const thought = firstId === undefined ? undefined : thoughts.items[firstId]
    const line = thought === undefined ? null : thoughtLine(Text, thought)
    if (e.props.isCallsOnly !== true) {
      if (line === null) return next(e)
      return (
        <Box flexDirection="column">
          {line}
          {await next(e)}
        </Box>
      )
    }
    const summary = summarize(e.props.calls.map(call => call.tool))
    return (
      <Box flexDirection="column">
        {line}
        {e.props.isActive ? (
          <Text wrap="truncate-end">
            <Text color={MUTED_YELLOW}>●</Text>
            <Text dimColor>{` ${summary}`}</Text>
          </Text>
        ) : (
          <Text dimColor wrap="truncate-end">{`… ${summary} …`}</Text>
        )}
      </Box>
    )
  })
}
