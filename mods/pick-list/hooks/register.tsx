import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import { parseOptions } from './parse'

const options = atom({ plugin: 'pick-list', key: 'options' } as const, [])
const picked = atom({ plugin: 'pick-list', key: 'picked' } as const, [])

export const register: Register = on => {
  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId || e.isAborted) return done
    const found = parseOptions(e.answer)
    await update($, options, () => found)
    await update($, picked, () => [])
    return done
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const list = await read($, options)
    const chosen = await read($, picked)
    if (!list.length || e.props.hasSurvey || e.props.isWorking) return next(e)

    const { Box, Button } = $.ui.resolve(e)
    const toggle = (n: number) => update($, picked, p => (p.includes(n) ? p.filter(x => x !== n) : [...p, n]))
    const send = async () => {
      let nums = ''
      await update($, picked, p => {
        nums = [...p].sort((a, b) => a - b).join(',')
        return []
      })
      if (!nums) return
      await update($, options, () => [])
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
