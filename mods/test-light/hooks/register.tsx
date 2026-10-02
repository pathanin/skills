import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Run } from '../types'
import { isTestCommand, verdict } from './parse'

const last = atom({ plugin: 'test-light', key: 'last' } as const, null)
// Bumped every minute so "3m ago" redraws instead of freezing.
const minute = atom({ plugin: 'test-light', key: 'minute' } as const, 0)

const EDITS = new Set(['Edit', 'Write', 'MultiEdit', 'NotebookEdit'])

const ago = (ms: number): string => {
  const m = Math.floor(ms / 60_000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  return `${Math.floor(m / 60)}h${m % 60 ? `${m % 60}m` : ''} ago`
}

export const register: Register = on => {
  on('session.start', ($, e, next) => {
    $.clock.every(60_000, () => void update($, minute, n => n + 1))
    return next(e)
  })

  // ponytail: main loop only, and only Edit/Write count as edits (a `sed -i` slips by).
  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    if (e.agentId || 'deny' in ran && ran.deny) return ran
    const input = e as unknown as { command?: string; file_path?: string; notebook_path?: string }

    if (e.tool === 'Bash' && input.command && isTestCommand(input.command)) {
      const run: Run = { ...verdict(String(ran.text ?? ''), Boolean(ran.isError)), at: await $.clock.now(), edited: [] }
      await update($, last, () => run)
    } else if (EDITS.has(e.tool) && !ran.isError) {
      const path = input.file_path ?? input.notebook_path
      if (path) {
        await update($, last, run =>
          run && !run.edited.includes(path) ? { ...run, edited: [...run.edited, path] } : run,
        )
      }
    }
    return ran
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const run = await read($, last)
    await read($, minute)
    if (!run || e.props.hasSurvey) return next(e)

    const { Box, Text } = $.ui.resolve(e)
    const counts = run.passed === undefined
      ? (run.ok ? 'tests passed' : 'tests failed')
      : run.failed
        ? `${run.failed} failed · ${run.passed} passed`
        : `${run.passed} passed`
    const n = run.edited.length

    return (
      <Box>
        <Text color={run.ok ? 'green' : 'red'}>{`${run.ok ? '✓' : '✗'} ${counts}`}</Text>
        <Text dimColor>{` · ${ago((await $.clock.now()) - run.at)}`}</Text>
        {n > 0 && <Text color="yellow">{` · ${n} file${n === 1 ? '' : 's'} edited since`}</Text>}
      </Box>
    )
  })
}
