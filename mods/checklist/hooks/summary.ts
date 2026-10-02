import type { Item } from '../types'

export const summary = (items: readonly Item[]): string => {
  if (!items.length) return 'Checklist cleared.'
  const done = items.filter(i => i.status === 'done').length
  const now = items.find(i => i.status === 'in_progress')
  const next = items.find(i => i.status === 'pending')
  const tail = now ? `now: ${now.text}` : next ? `next: ${next.text}` : 'all done'
  return `${done}/${items.length} done · ${tail}`
}
