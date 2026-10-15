// Splits markdown into paragraphs on blank lines, keeping a fenced code
// block (``` or ~~~) and an indented continuation whole even across blank lines.
export function splitParagraphs(text: string): string[] {
  const chunks: string[] = []
  let current: string[] = []
  let fence: string | null = null
  let pendingBlank = false

  const flush = () => {
    if (current.some(line => line.trim() !== '')) {
      chunks.push(current.join('\n').replace(/^\n+|\n+$/g, ''))
    }
    current = []
  }

  for (const line of text.split('\n')) {
    const marker = /^\s*(`{3,}|~{3,})/.exec(line)?.[1]
    if (marker !== undefined) {
      if (fence === null) {
        fence = marker
      } else if (marker[0] === fence[0] && marker.length >= fence.length) {
        fence = null
      }
    }

    const isBlank = fence === null && line.trim() === '' && marker === undefined
    const isIndented = /^\s/.test(line) && line.trim() !== ''
    if (isBlank) {
      pendingBlank = true
      continue
    }
    if (pendingBlank) {
      // An indented line after a blank one belongs to the block above it
      // (a nested list item, a list item's continuation).
      if (isIndented) {
        current.push('')
      } else {
        flush()
      }
      pendingBlank = false
    }
    current.push(line)
  }
  flush()

  return chunks
}

// Turns text into a markdown blockquote followed by an empty line to type on.
export function quote(text: string): string {
  return text.replace(/\n+$/, '').replace(/^/gm, '> ') + '\n\n'
}

// Markdown and drawn text reduced to comparable words: no markup, one space.
function plain(text: string): string {
  return text
    .replace(/[*_`#>|[\]()~]/g, ' ')
    .replace(/^\s*([-+]|\d+\.)\s+/gm, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

// Which paragraph the selection ends in, by the last words of its last line as
// drawn; the last paragraph when no paragraph holds them.
export function paragraphOfSelection(paragraphs: string[], selected: string): number {
  const lastLine = selected.split('\n').filter(line => line.trim() !== '').pop() ?? ''
  const tail = plain(lastLine).slice(-40).trim()
  for (let i = paragraphs.length - 1; i >= 0; i--) {
    if (tail !== '' && plain(paragraphs[i] ?? '').includes(tail)) {
      return i
    }
  }
  return paragraphs.length - 1
}
