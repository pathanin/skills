import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Picker, Selected } from '../types'
import { paragraphOfSelection, quote, splitParagraphs } from './paragraphs'

const PANE = 'reply-picker'
const POLL_MS = 300
const lastReply = atom({ plugin: 'reply-quote', key: 'lastReply' } as const, [] as string[])
const picker = atom({ plugin: 'reply-quote', key: 'picker' } as const, null as Picker | null)
const selected = atom({ plugin: 'reply-quote', key: 'selected' } as const, null as Selected | null)

async function fillQuote($: EngineInterface, text: string) {
  const filled = await $.prompt.fill({ text: quote(text), mode: 'insert' })
  if (!filled.isFilled) {
    $.ui.toast('Could not put the quote in the prompt')
  }
}

async function readClipboard($: EngineInterface): Promise<string> {
  try {
    const ran = await $.process.run(['pbpaste'], { timeoutMs: 2000 })
    return ran.exitCode === 0 ? ran.stdout : ''
  } catch {
    return ''
  }
}

function oneLine(text: string, columns: number): string {
  const flat = text.replace(/\s+/g, ' ').trim()
  return flat.length > columns ? flat.slice(0, Math.max(1, columns - 1)) + '…' : flat
}

export const register: Register = on => {
  // The selection last quoted, so its button stays away until a new one.
  let usedText = ''

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'reply',
      description: 'Quote part of the last reply: pick a paragraph, the selection or the clipboard',
      argumentHint: '[paragraph number | text]',
    })

    // No event says the selection changed, so look for it a few times a second.
    // Selection is only seen in fullscreen; elsewhere this finds nothing.
    $.clock.every(POLL_MS, async () => {
      const now = await $.ui.selection()
      const text = now?.text.trim() ?? ''
      if (text === '') {
        usedText = ''
      }
      const fresh: Selected | null =
        now !== undefined && now.requestId !== undefined && text !== '' && now.text !== usedText
          ? { text: now.text, requestId: now.requestId }
          : null
      const shown = await read($, selected)
      if (shown?.text !== fresh?.text || shown?.requestId !== fresh?.requestId) {
        await update($, selected, () => fresh)
      }
    })
    return next(e)
  })

  // Remember the text of the latest reply in the main conversation.
  on('session.append', async ($, e, next) => {
    const stored = await next(e)
    if (e.agentId === undefined) {
      if (e.door === 'prompt') {
        await update($, lastReply, () => [])
        await update($, picker, () => null)
      } else if (e.door === 'response') {
        const texts = e.message.content.flatMap(block =>
          block.type === 'text' && typeof block.text === 'string' && block.text.trim() !== ''
            ? [block.text]
            : [],
        )
        if (texts.length > 0) {
          await update($, lastReply, blocks => [...blocks, ...texts])
        }
      }
    }
    return stored
  }).catch(($, e, next) => next(e))

  on('command.run', { command: 'reply' }, async ($, e) => {
    const args = e.args.trim()
    const paragraphs = splitParagraphs((await read($, lastReply)).join('\n\n'))

    if (/^\d+$/.test(args)) {
      const paragraph = paragraphs[Number(args) - 1]
      if (paragraph === undefined) {
        return { text: `The last reply has ${paragraphs.length} paragraphs.` }
      }
      await fillQuote($, paragraph)
      return { text: `Quoted paragraph ${args}.` }
    }

    if (args !== '') {
      await fillQuote($, args)
      return { text: 'Quoted.' }
    }

    // The engine keeps the last selection after a click elsewhere, so it is
    // offered in the list rather than quoted straight away.
    const selection = (await $.ui.selection())?.text ?? ''
    const clipboard = await readClipboard($)
    const sel = selection.trim() === '' ? '' : selection
    const clip = clipboard.trim() === '' || clipboard.trim() === sel.trim() ? '' : clipboard
    if (paragraphs.length === 0 && sel === '' && clip === '') {
      return { text: 'Nothing to quote yet: no reply, selection or clipboard.' }
    }

    const seq = ((await read($, picker))?.seq ?? 0) + 1
    await update($, picker, () => ({ seq, paragraphs, clip, selection: sel }))

    // Fullscreen: the list is drawn as this command's output, to click on.
    // Otherwise: a small keyboard list above the prompt.
    if (e.presentation.isFullscreen) {
      return { text: `Pick what to quote (list ${seq}).` }
    }
    await $.ui.open({
      id: PANE,
      title: 'Reply to…',
      focus: true,
      closeOnEscape: true,
      rows: paragraphs.length + 1 + (sel === '' ? 0 : 1) + (clip === '' ? 0 : 1),
    })
    return { text: 'Pick what to quote.' }
  })

  // The keyboard list (not fullscreen).
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Text } = $.ui.resolve(e)
    const list = await read($, picker)
    const width = Math.max(10, e.props.bodyColumns - 8)

    if (list === null) {
      return <Text dimColor>Nothing to pick from.</Text>
    }

    const pick = async (text: string) => {
      await update($, picker, () => null)
      await $.ui.close({ id: PANE })
      await fillQuote($, text)
    }
    const hasSel = list.selection !== ''
    const hasClip = list.clip !== ''

    return (
      <Box flexDirection="column">
        {hasSel && (
          <Button key="sel" hotkey="s" plain autoFocus onPress={() => pick(list.selection)}>
            Selection: <Text dimColor>{oneLine(list.selection, width - 11)}</Text>
          </Button>
        )}
        {hasClip && (
          <Button
            key="clip"
            hotkey="c"
            plain
            autoFocus={hasSel ? undefined : true}
            onPress={() => pick(list.clip)}
          >
            Clipboard: <Text dimColor>{oneLine(list.clip, width - 11)}</Text>
          </Button>
        )}
        {list.paragraphs.map((paragraph, i) => (
          <Button
            key={`para-${i}`}
            hotkey={i < 9 ? String(i + 1) : undefined}
            plain
            autoFocus={!hasSel && !hasClip && i === 0 ? true : undefined}
            onPress={() => pick(paragraph)}
          >
            {i < 9 ? '' : `${i + 1}. `}
            {oneLine(paragraph, width)}
          </Button>
        ))}
        <Text dimColor>number or ↑↓ Enter to quote · Esc to cancel</Text>
      </Box>
    )
  })

  // The click list (fullscreen), drawn in place of the command's output line.
  on('ui.render', { component: 'CommandOutput', props: { command: 'reply' } }, async ($, e, next) => {
    const seq = /\(list (\d+)\)/.exec(e.props.text)?.[1]
    if (seq === undefined) {
      return next(e)
    }

    const { Box, Button, Text } = $.ui.resolve(e)
    const list = await read($, picker)
    if (list === null || String(list.seq) !== seq) {
      return (
        <Box paddingLeft={2}>
          <Text dimColor>Reply list closed.</Text>
        </Box>
      )
    }

    const width = Math.max(10, (e.viewport?.columns ?? 80) - 12)
    const pick = async (text: string) => {
      await update($, picker, () => null)
      await fillQuote($, text)
    }

    return (
      <Box flexDirection="column" paddingLeft={2}>
        <Text dimColor>Click what to quote:</Text>
        {list.selection !== '' && (
          <Button key="out-sel" plain onPress={() => pick(list.selection)}>
            {'↩ Selection: '}
            <Text dimColor>{oneLine(list.selection, width - 13)}</Text>
          </Button>
        )}
        {list.clip !== '' && (
          <Button key="out-clip" plain onPress={() => pick(list.clip)}>
            {'↩ Clipboard: '}
            <Text dimColor>{oneLine(list.clip, width - 13)}</Text>
          </Button>
        )}
        {list.paragraphs.map((paragraph, i) => (
          <Button key={`out-para-${i}`} plain onPress={() => pick(paragraph)}>
            {`↩ ${i + 1}. `}
            {oneLine(paragraph, width)}
          </Button>
        ))}
      </Box>
    )
  })

  // Fullscreen only: a ↩ on each paragraph, shown on hover, quoting it; and a
  // "Reply to selection" button under the paragraph that holds the selection.
  on('ui.render', { component: 'AssistantMessage' }, async ($, e, next) => {
    if (
      e.surface !== 'terminal' ||
      e.viewport?.isFullscreen !== true ||
      e.props.isSummary === true
    ) {
      return next(e)
    }

    const paragraphs = splitParagraphs(e.props.text)
    if (paragraphs.length === 0) {
      return next(e)
    }

    const { Box, Button, Markdown, Text } = $.ui.resolve(e)
    const messageId = e.requestId
    const selection = await read($, selected)
    const selectedHere = selection !== null && selection.requestId === messageId ? selection : null
    const selectionAt = selectedHere === null ? -1 : paragraphOfSelection(paragraphs, selectedHere.text)

    return (
      <Box flexDirection="row">
        <Box width={2} flexShrink={0}>
          <Text>{e.props.isFirstOfReply ? '⏺' : ' '}</Text>
        </Box>
        <Box flexDirection="column" flexGrow={1} flexShrink={1} gap={1}>
          {paragraphs.map((paragraph, i) => (
            <Box key={`p-${i}`} flexDirection="column">
              <Box flexDirection="row">
                <Box flexGrow={1} flexShrink={1} paddingRight={2}>
                  <Markdown text={paragraph} />
                </Box>
                <Box
                  position="absolute"
                  top={0}
                  right={0}
                  display="none"
                  hover={{ display: 'flex' }}
                >
                  <Button
                    key={`reply-${i}`}
                    label="↩"
                    plain
                    dimColor
                    onPress={() => fillQuote($, paragraph)}
                  />
                </Box>
              </Box>
              {selectedHere !== null && selectionAt === i && (
                <Button
                  key="reply-selection"
                  variant="primary"
                  onPress={async () => {
                    usedText = selectedHere.text
                    await update($, selected, () => null)
                    await fillQuote($, selectedHere.text)
                  }}
                >
                  ↩ Reply to selection
                </Button>
              )}
            </Box>
          ))}
        </Box>
      </Box>
    )
  })
}
