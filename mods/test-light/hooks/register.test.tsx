import { expect, mock, test } from 'claude-code/testing'

import { isTestCommand, verdict } from './parse'

test('spots test commands, ignores the rest', () => {
  expect(isTestCommand('cd repo && python3 -m pytest -q')).toBe(true)
  expect(isTestCommand('npm test')).toBe(true)
  expect(isTestCommand('node hooks/git-guard.mjs --self-test')).toBe(true)
  expect(isTestCommand('python3 -m unittest discover')).toBe(true)
  expect(isTestCommand('claude plugin test ./mod')).toBe(true)
  expect(isTestCommand('git status')).toBe(false)
  expect(isTestCommand('grep -r pytest .')).toBe(false)
})

test('reads pass and fail counts', () => {
  expect(verdict('==== 142 passed in 3.1s ====', false)).toEqual({ ok: true, passed: 142, failed: 0 })
  expect(verdict('== 2 failed, 140 passed in 3s ==', true)).toEqual({ ok: false, passed: 140, failed: 2 })
  expect(verdict('Ran 12 tests in 0.4s\n\nOK', false)).toEqual({ ok: true, passed: 12, failed: 0 })
  expect(verdict('Ran 12 tests\n\nFAILED (failures=1, errors=2)', true)).toEqual({ ok: false, passed: 9, failed: 3 })
  expect(verdict('Tests:       1 failed, 30 passed, 31 total', true)).toEqual({ ok: false, passed: 30, failed: 1 })
  expect(verdict('test result: ok. 8 passed; 0 failed', false)).toEqual({ ok: true, passed: 8, failed: 0 })
  expect(verdict(' 7 pass\n 0 fail\nRan 7 tests across 1 file.', false)).toEqual({ ok: true, passed: 7, failed: 0 })
  expect(verdict('ok — 14 cases', false)).toEqual({ ok: true })
  expect(verdict('Exit code 1\nboom', true)).toEqual({ ok: false })
})

for (const surface of ['terminal', 'desktop'] as const) {
  test(`${surface}: band shows the run and edits since`, async ($, on) => {
    mock.clock(on, { now: 1_000_000 })
    on('tool.call', { tool: 'Bash' }, () => ({ result: {}, text: '5 passed in 0.2s' }))
    on('tool.call', { tool: 'Edit' }, () => ({ result: {}, text: 'ok' }))
    on('ui.render', ($, e) => { const { Box } = $.ui.resolve(e); return <Box /> })
    const band = await $.ui.mount({ plugin: 'test-light', surface, component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false } })
    expect(await band.find({ text: /passed/ })).toBeUndefined()

    await $.tool.call({ tool: 'Bash', command: 'pytest -q' })
    await $.tool.call({ tool: 'Edit', file_path: '/a.py', old_string: 'x', new_string: 'y' })
    await $.tool.call({ tool: 'Edit', file_path: '/a.py', old_string: 'y', new_string: 'z' })
    expect(await band.find({ text: /✓ 5 passed/ })).toBeDefined()
    expect(await band.find({ text: /just now/ })).toBeDefined()
    expect(await band.find({ text: /1 file edited since/ })).toBeDefined()
  })
}
