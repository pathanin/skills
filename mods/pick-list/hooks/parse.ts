import type { Option } from '../types'

// A top-level numbered item: "1. x", "2) x", "**3. x**", "### 4. x", or a table row "| 5 | x |".
// Indented ones are sub-steps.
const ITEM = /^ ?(?:#{1,4}\s+)?(?:\*\*)?(\d{1,2})[.)]\s+(.+)$/
const ROW = /^\|\s*(\d{1,2})\s*\|\s*([^|]+)\|/

const clean = (text: string): string =>
  text.replace(/\*\*|`/g, '').trim().slice(0, 90)

// A question mark ending a sentence, not one inside a URL.
const ASKS = /\?(?:[*_)\s]|$)/

// The longest run of items numbered 1, 2, 3… (the later one on a tie), if it has two or more.
// Longest, not last: replies often end with a short "Needs your input" list.
// A reply that asks nothing is a report, so its lists are results, not choices.
export const parseOptions = (answer: string): Option[] => {
  if (!ASKS.test(answer)) return []
  const lists: Option[][] = []
  for (const line of answer.split('\n')) {
    const m = line.match(ITEM) ?? line.match(ROW)
    if (!m) continue
    const n = Number(m[1])
    const current = lists[lists.length - 1]
    if (n === 1) lists.push([{ n, title: clean(m[2]) }])
    else if (current && n === current.length + 1) current.push({ n, title: clean(m[2]) })
  }
  const best = lists.reduce<Option[]>((a, b) => (b.length >= a.length ? b : a), [])
  return best.length >= 2 ? best : []
}
