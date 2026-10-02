import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import { parseOptions } from './parse'

const PANE = 'pick-list'
const options = atom({ plugin: 'pick-list', key: 'options' } as const, [])
const picked = atom({ plugin: 'pick-list', key: 'picked' } as const, [])

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'picks', description: 'Tick the numbered options from my last reply' })
    return next(e)
  })

  on('command.run', { command: 'picks' }, async $ => {
    await $.ui.open({ id: PANE, title: 'Pick list' })
    return { text: 'Pick list opened.' }
  })

  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId || e.isAborted) return done
    const found = parseOptions(e.answer)
    await update($, options, () => found)
    await update($, picked, () => [])
    if (found.length) void $.ui.open({ id: PANE, title: 'Pick list' })
    return done
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Text } = $.ui.resolve(e)
    const list = await read($, options)
    const chosen = await read($, picked)

    if (!list.length) return <Text dimColor>No numbered options in my last reply.</Text>

    const toggle = (n: number) => update($, picked, p => (p.includes(n) ? p.filter(x => x !== n) : [...p, n]))
    const send = async () => {
      let nums = ''
      await update($, picked, p => {
        nums = [...p].sort((a, b) => a - b).join(',')
        return []
      })
      if (!nums) return
      void $.prompt.submit({ text: `do ${nums}`, asUser: true })
    }

    return (
      <Box flexDirection="column">
        {list.map(o => (
          <Button
            key={`opt-${o.n}`}
            plain
            hotkey={o.n <= 9 ? String(o.n) : undefined}
            label={`${chosen.includes(o.n) ? '☑' : '☐'} ${o.title}`}
            onPress={() => toggle(o.n)}
          />
        ))}
        {chosen.length > 0 && (
          <Button key="send" variant="primary" hotkey="d" label={`Do ${[...chosen].sort((a, b) => a - b).join(', ')}`} onPress={send} />
        )}
      </Box>
    )
  })
}
