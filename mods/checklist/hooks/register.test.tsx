import { expect, test } from 'claude-code/testing'

import { summary } from './summary'

const TOOL = 'mcp__checklist__checklist'

test('summary names the count and what is next', () => {
  expect(summary([])).toBe('Checklist cleared.')
  expect(summary([
    { text: 'Read code', status: 'done' },
    { text: 'Write tests', status: 'in_progress' },
    { text: 'Ship', status: 'pending' },
  ])).toBe('1/3 done · now: Write tests')
  expect(summary([{ text: 'a', status: 'done' }, { text: 'b', status: 'pending' }])).toBe('1/2 done · next: b')
  expect(summary([{ text: 'a', status: 'done' }])).toBe('1/1 done · all done')
})

for (const surface of ['terminal', 'desktop'] as const) {
  test(`${surface}: a checklist call fills the pane; a subagent's does not`, async ($, on) => {
    on('ui.open', () => ({ value: undefined }))
    on('ui.status', () => ({ value: undefined }))
    const lines = async () => (await pane.findAll({ type: 'Text' })).map(t => t.text)
    const pane = await $.ui.mount({ plugin: 'checklist', surface, component: 'Pane', requestId: 'checklist', props: {} })
    expect((await pane.find({ type: 'Text' }))?.text).toContain('No checklist')

    const ran = await $.tool.call({ tool: TOOL, items: [
      { text: 'Read code', status: 'done' },
      { text: 'Write tests', status: 'in_progress' },
    ] })
    expect(String('result' in ran ? ran.result : '')).toContain('1/2 done')
    expect(await lines()).toEqual(['Progress 1/2', '☑ Read code', '▶ Write tests'])

    await $.tool.call({ tool: TOOL, agentId: 'sub', items: [{ text: 'other', status: 'pending' }] })
    expect((await lines())[1]).toBe('☑ Read code')
  })
}
