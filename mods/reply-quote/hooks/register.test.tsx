import { describe, expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

import { paragraphOfSelection, splitParagraphs } from './paragraphs'

const TEXT = [
  'First paragraph.',
  '',
  'Second paragraph,\nover two lines.',
  '',
  '```js',
  'const a = 1',
  '',
  'const b = 2',
  '```',
].join('\n')

const FULLSCREEN = { columns: 100, rows: 40, isFullscreen: true }

function runReply($: Engine, args = '', isFullscreen = false) {
  return $.command.run({
    command: 'reply',
    args,
    origin: { kind: 'composer' },
    presentation: { isFullscreen, columns: 100 },
  })
}

// Stands in for the engine: records prompt fills, answers selection and
// clipboard, and remembers which panes were opened and closed.
function fakeEngine(on: On, opts: { selection?: { text: string; requestId?: string }; clipboard?: string } = {}) {
  const filled: string[] = []
  const panes: string[] = []
  on('prompt.fill', ($, e) => {
    filled.push(e.text)
    return { isFilled: true }
  })
  on('ui.selection', () => ({ value: opts.selection }))
  on('process.run', () => ({
    value: {
      exitCode: 0,
      stdout: opts.clipboard ?? '',
      stderr: '',
      isStdoutTruncated: false,
      isStderrTruncated: false,
    },
  }))
  on('ui.open', ($, e) => {
    panes.push(`open ${e.id}`)
    return { value: { isPlaced: true } }
  })
  on('ui.close', ($, e) => {
    panes.push(`close ${e.id}`)
    return { value: undefined }
  })
  return { filled, panes }
}

async function appendRow($: Engine, door: 'prompt' | 'response', text: string) {
  await $.session.append({
    door,
    uuid: crypto.randomUUID(),
    origin: door === 'prompt' ? { kind: 'composer' } : { kind: 'model', model: 'claude-opus-5-5' },
    message: {
      type: door === 'prompt' ? 'user' : 'assistant',
      role: door === 'prompt' ? 'user' : 'assistant',
      content: [{ type: 'text', text }],
    },
  })
}

function mountMessage($: Engine, extra: object = {}) {
  return $.ui.mount({
    plugin: 'reply-quote',
    surface: 'terminal',
    component: 'AssistantMessage',
    requestId: 'msg-1',
    props: { text: TEXT, isFirstOfReply: true },
    viewport: FULLSCREEN,
    ...extra,
  })
}

// A drawn tree without its absolutely placed boxes: what takes room on screen.
function inFlow(node: unknown): unknown {
  if (Array.isArray(node)) {
    return node.filter(child => !isAbsolute(child)).map(inFlow)
  }
  if (node !== null && typeof node === 'object') {
    return Object.fromEntries(Object.entries(node).map(([k, v]) => [k, inFlow(v)]))
  }
  return node
}

function isAbsolute(node: unknown): boolean {
  const props = (node as { props?: { position?: string } } | null)?.props
  return props?.position === 'absolute'
}

function mountPicker($: Engine) {
  return $.ui.mount({
    plugin: 'reply-quote',
    surface: 'terminal',
    component: 'Pane',
    requestId: 'reply-picker',
    props: {
      title: 'Reply to…',
      isFocused: true,
      bodyColumns: 80,
      placement: 'inline',
      scroll: { offset: 0, bodyRows: 20 },
      view: {},
    },
  })
}

describe('splitParagraphs', () => {
  test('keeps indented continuations with the list item above', async () => {
    expect(splitParagraphs('1. Step\n\n    detail\n\n  - nested\n\n- next')).toEqual([
      '1. Step\n\n    detail\n\n  - nested',
      '- next',
    ])
  })

  test('keeps a fenced block with blank lines whole', async () => {
    expect(splitParagraphs(TEXT)).toEqual([
      'First paragraph.',
      'Second paragraph,\nover two lines.',
      '```js\nconst a = 1\n\nconst b = 2\n```',
    ])
  })
})

describe('paragraphOfSelection', () => {
  test('finds the paragraph the selection ends in, ignoring markdown', async () => {
    const paragraphs = ['Intro with **bold** words.', '- a list item about `code` here', 'Last one.']
    expect(paragraphOfSelection(paragraphs, 'bold words')).toBe(0)
    expect(paragraphOfSelection(paragraphs, 'item about code')).toBe(1)
    expect(paragraphOfSelection(paragraphs, 'words.\n\na list item about code here')).toBe(1)
    expect(paragraphOfSelection(paragraphs, 'not in any')).toBe(2)
  })
})

describe('/reply without fullscreen', () => {
  test('/reply 2 quotes paragraph 2 of the latest reply only', async ($, on) => {
    const { filled } = fakeEngine(on)
    await appendRow($, 'prompt', 'old question')
    await appendRow($, 'response', 'Old answer.')
    await appendRow($, 'prompt', 'new question')
    await appendRow($, 'response', 'Intro.')
    await appendRow($, 'response', 'Point one.\n\nPoint two.')

    await runReply($, '2')
    expect(filled).toEqual(['> Point one.\n\n'])

    const result = await runReply($, '9')
    expect(result).toEqual(expect.objectContaining({ text: 'The last reply has 3 paragraphs.' }))
  })

  test('/reply <text> quotes the text given', async ($, on) => {
    const { filled } = fakeEngine(on)
    await runReply($, 'pasted words')
    expect(filled).toEqual(['> pasted words\n\n'])
  })

  test('/reply opens the picker; a number quotes that paragraph and closes it', async ($, on) => {
    const { filled, panes } = fakeEngine(on, { clipboard: 'copied\nline two' })
    await appendRow($, 'response', TEXT)

    await runReply($)
    expect(panes).toEqual(['open reply-picker'])

    const ui = await mountPicker($)
    expect((await ui.findAll({ type: 'Button' })).length).toBe(4)

    await ui.press({ key: 'para-1' })
    expect(filled).toEqual(['> Second paragraph,\n> over two lines.\n\n'])
    expect(panes).toEqual(['open reply-picker', 'close reply-picker'])
  })

  test('the picker quotes the clipboard', async ($, on) => {
    const { filled } = fakeEngine(on, { clipboard: 'copied\nline two' })
    await appendRow($, 'response', TEXT)
    await runReply($)

    const ui = await mountPicker($)
    await ui.press({ key: 'clip' })
    expect(filled).toEqual(['> copied\n> line two\n\n'])
  })

  test('says so when there is no reply and the clipboard is empty', async ($, on) => {
    const { panes } = fakeEngine(on)
    const result = await runReply($)
    expect(result).toEqual(expect.objectContaining({ text: expect.stringContaining('Nothing to quote') }))
    expect(panes).toEqual([])
  })
})

describe('fullscreen', () => {
  test('/reply draws a click list as its output; a click quotes and closes it', async ($, on) => {
    const { filled, panes } = fakeEngine(on, { clipboard: 'copied' })
    await appendRow($, 'response', TEXT)

    const result = await runReply($, '', true)
    expect(result).toEqual(expect.objectContaining({ text: 'Pick what to quote (list 1).' }))
    expect(panes).toEqual([])

    const ui = await $.ui.mount({
      plugin: 'reply-quote',
      surface: 'terminal',
      component: 'CommandOutput',
      props: { command: 'reply', args: '', text: 'Pick what to quote (list 1).', isErrored: false },
      viewport: FULLSCREEN,
    })
    expect((await ui.findAll({ type: 'Button' })).length).toBe(4)

    await ui.press({ key: 'out-para-2' })
    expect(filled).toEqual(['> ```js\n> const a = 1\n> \n> const b = 2\n> ```\n\n'])
    expect((await ui.findAll({ type: 'Button' })).length).toBe(0)
    expect((await ui.findAll({ type: 'Text', text: 'Reply list closed.' })).length).toBe(1)
  })

  test('a selection shows "Reply to selection" under its paragraph', async ($, on) => {
    const clock = mock.clock(on)
    const { filled } = fakeEngine(on, { selection: { text: 'over two', requestId: 'msg-1' } })
    on('command.register', () => ({ value: { command: 'reply' } }))
    on('session.start', () => ({ cwd: '/' }))
    await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })

    const ui = await mountMessage($)
    expect((await ui.findAll({ key: 'reply-selection' })).length).toBe(0)

    await clock.advance(400)
    const shown = await ui.findAll({ key: 'reply-selection' })
    expect(shown.length).toBe(1)

    await ui.press({ key: 'reply-selection' })
    expect(filled).toEqual(['> over two\n\n'])

    // Quoted once, the button stays away while the same text is selected.
    await clock.advance(400)
    expect((await ui.findAll({ key: 'reply-selection' })).length).toBe(0)
  })

  test('"Reply to selection" appears without moving the text', async ($, on) => {
    // Drawn in the flow, the button pushed the rows below it down while the
    // person was still selecting, so the highlight slid onto other text.
    const clock = mock.clock(on)
    fakeEngine(on, { selection: { text: 'over two', requestId: 'msg-1' } })
    on('command.register', () => ({ value: { command: 'reply' } }))
    on('session.start', () => ({ cwd: '/' }))
    await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })

    const ui = await mountMessage($)
    const before = await ui.drawn()
    await clock.advance(400)
    expect((await ui.findAll({ key: 'reply-selection' })).length).toBe(1)
    expect(inFlow(await ui.drawn())).toEqual(inFlow(before))
  })

  test('/reply offers a selection in the list instead of quoting it at once', async ($, on) => {
    // The engine keeps the last selection after a click elsewhere, so quoting
    // it straight away put stale text in the prompt.
    const { filled } = fakeEngine(on, {
      selection: { text: 'old pick', requestId: 'msg-1' },
      clipboard: 'old pick',
    })
    await appendRow($, 'response', TEXT)

    const result = await runReply($, '', true)
    expect(result).toEqual(expect.objectContaining({ text: 'Pick what to quote (list 1).' }))
    expect(filled).toEqual([])

    const ui = await $.ui.mount({
      plugin: 'reply-quote',
      surface: 'terminal',
      component: 'CommandOutput',
      props: { command: 'reply', args: '', text: 'Pick what to quote (list 1).', isErrored: false },
      viewport: FULLSCREEN,
    })
    // Selection plus three paragraphs; the clipboard holds the same text, so it is not repeated.
    expect((await ui.findAll({ type: 'Button' })).length).toBe(4)
    expect((await ui.findAll({ key: 'out-clip' })).length).toBe(0)

    await ui.press({ key: 'out-sel' })
    expect(filled).toEqual(['> old pick\n\n'])
  })

  test('one ↩ per paragraph; pressing quotes that paragraph', async ($, on) => {
    const { filled } = fakeEngine(on)
    const ui = await mountMessage($)
    expect((await ui.findAll({ type: 'Button' })).length).toBe(3)

    await ui.press({ key: 'reply-1' })
    expect(filled).toEqual(['> Second paragraph,\n> over two lines.\n\n'])
  })

  test('↩ quotes its paragraph even while a selection is remembered', async ($, on) => {
    const { filled } = fakeEngine(on, { selection: { text: 'over two', requestId: 'msg-1' } })
    const ui = await mountMessage($)
    await ui.press({ key: 'reply-0' })
    expect(filled).toEqual(['> First paragraph.\n\n'])
  })

  test('replies draw as normal outside fullscreen and for summaries', async ($, on) => {
    on('ui.render', { component: 'AssistantMessage' }, ($, e) => {
      const { Text } = $.ui.resolve(e)
      return <Text>engine</Text>
    })
    for (const extra of [
      { viewport: { columns: 100, rows: 40, isFullscreen: false } },
      { props: { text: TEXT, isFirstOfReply: true, isSummary: true as const } },
    ]) {
      const ui = await mountMessage($, extra)
      expect((await ui.findAll({ type: 'Button' })).length).toBe(0)
      expect((await ui.findAll({ type: 'Text', text: 'engine' })).length).toBe(1)
      await ui.unmount()
    }
  })
})
