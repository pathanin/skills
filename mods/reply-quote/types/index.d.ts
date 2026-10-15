// The list `/reply` offers: what it held when opened, by its run number.
export type Picker = { seq: number; paragraphs: string[]; clip: string; selection: string }

// What is selected with the mouse now (fullscreen), and in which message.
export type Selected = { text: string; requestId: string }

declare module 'claude-code' {
  interface PluginState {
    'reply-quote': {
      // The text blocks of Claude's latest reply, in order.
      lastReply: string[]
      // The open `/reply` list; null once picked from or a new prompt is sent.
      picker: Picker | null
      // The current selection inside a reply; null when none, or already quoted.
      selected: Selected | null
    }
  }
}
