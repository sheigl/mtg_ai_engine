// Debug log types for feature 011-observer-ai-commentary

export type DebugEntryType = 'prompt_response' | 'commentary'
export type Rating = 'good' | 'acceptable' | 'suboptimal'

export interface DebugEntry {
  entry_id: string
  entry_type: DebugEntryType
  source: string        // player name (e.g. "Llama") or "Observer AI"
  turn: number
  phase: string
  step: string
  timestamp: number
  prompt: string
  response: string
  is_complete: boolean
  rating?: Rating
  explanation?: string
  alternative?: string
  thinking?: string     // Extended thinking/reasoning tokens (collapsible)
}

export interface DebugLog {
  game_id: string
  entries: DebugEntry[]
}
