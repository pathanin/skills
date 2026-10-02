import { expect, test } from 'claude-code/testing'

import { parseOptions } from './parse'

test('finds a plain numbered list', () => {
  const text = 'Options:\n\n1. Fix the lock\n2. Add **progress** bar\n3. `Speed` up scan\n\nWhich?'
  expect(parseOptions(text)).toEqual([
    { n: 1, title: 'Fix the lock' },
    { n: 2, title: 'Add progress bar' },
    { n: 3, title: 'Speed up scan' },
  ])
})

test('takes bold headings and skips nested steps', () => {
  const text = '**1. test-light (band)**\nbody\n   1. sub step\n   2. sub step\n**2. pick-list (pane)**\nbody\n\nWhich one?'
  expect(parseOptions(text).map(o => o.title)).toEqual(['test-light (band)', 'pick-list (pane)'])
})

test('picks the longest list, not the trailing questions', () => {
  const text = '1. found a\n2. found b\n\n**1. idea one**\n**2. idea two**\n**3. idea three**\n\n## Needs your input\n\n1. Which?\n2. Extend?'
  expect(parseOptions(text).map(o => o.title)).toEqual(['idea one', 'idea two', 'idea three'])
})

test('reads a table with a # column', () => {
  const text = '| # | Location | Today |\n|---|---|---|\n| 1 | **Terminal** progress | frozen |\n| 2 | **Web** modal | instant |\n\nFix which?'
  expect(parseOptions(text)).toEqual([
    { n: 1, title: 'Terminal progress' },
    { n: 2, title: 'Web modal' },
  ])
})

test('no list, or one item, gives nothing', () => {
  expect(parseOptions('All done, tests pass.')).toEqual([])
  expect(parseOptions('1. only one')).toEqual([])
  expect(parseOptions('Released v0.4.4 on 2026-10-02.')).toEqual([])
})

test('a result report that asks nothing gives nothing', () => {
  const text = 'The demo is finished:\n\n1. **Count to 1M:** the sum came to 499,999,500,000.\n2. **Hash a file:** the SHA-256 starts with c7dd.\n3. **Report result:** this message.\n\nNo files were created.'
  expect(parseOptions(text)).toEqual([])
  expect(parseOptions('See https://x.io/?a=1\n\n1. done a\n2. done b')).toEqual([])
})

for (const surface of ['terminal', 'desktop'] as const) {
  test(`${surface}: ticking options in the band sends "do 1,3"`, async ($, on) => {
    const sent: string[] = []
    on('turn.complete', () => ({ text: '' }))
    on('ui.render', ($, e) => { const { Box } = $.ui.resolve(e); return <Box /> })
    on('prompt.submit', (_, e) => { sent.push(e.text); return { text: '' } })
    const band = await $.ui.mount({ plugin: 'pick-list', surface, component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false } })
    expect(await band.find({ key: 'opt-1' })).toBeUndefined()

    await $.turn.complete({ answer: 'Which?\n1. alpha\n2. beta\n3. gamma', durationMs: 1, isAborted: false, turnId: 't', reason: 'answer' })
    await band.press({ key: 'opt-3' })
    await band.press({ key: 'opt-1' })
    await band.press({ key: 'send' })
    expect(sent).toEqual(['do 1,3'])
    expect(await band.find({ key: 'opt-1' })).toBeUndefined()
  })

  test(`${surface}: band hides while a turn runs`, async ($, on) => {
    on('turn.complete', () => ({ text: '' }))
    on('ui.render', ($, e) => { const { Box } = $.ui.resolve(e); return <Box /> })
    const band = await $.ui.mount({ plugin: 'pick-list', surface, component: 'AbovePrompt', props: { hasSurvey: false, isWorking: true } })
    await $.turn.complete({ answer: '1. alpha\n2. beta', durationMs: 1, isAborted: false, turnId: 't', reason: 'answer' })
    expect(await band.find({ key: 'opt-1' })).toBeUndefined()
  })
}
