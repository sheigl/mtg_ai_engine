import { useEffect, useRef, useState } from 'react'
import { useDebugLog } from '../hooks/useDebugLog'
import { PromptResponseBlock } from './PromptResponseBlock'
import { CommentaryBlock } from './CommentaryBlock'
import type { DebugEntry } from '../types/debug'
import '../styles/debug.css'

const LS_KEY = 'mtg_debug_panel_enabled'
const PAGE_SIZE = 10

interface Props {
  gameId: string
  isGameOver: boolean
  debugEnabled?: boolean
}

async function postPause(gameId: string, paused: boolean) {
  await fetch(`/game/${gameId}/${paused ? 'pause' : 'resume'}`, { method: 'POST' })
}

export function DebugPanel({ gameId, isGameOver, debugEnabled }: Props) {
  const [enabled, setEnabled] = useState<boolean>(() => {
    if (debugEnabled) return true
    try { return localStorage.getItem(LS_KEY) === 'true' } catch { return false }
  })
  const [open, setOpen] = useState(enabled)
  const [showAll, setShowAll] = useState(false)
  const [paused, setPaused] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const { entries, isLoading } = useDebugLog(gameId, enabled, isGameOver)

  const allSources = Array.from(
    new Set(entries.filter(e => e.source !== 'Observer AI').map(e => e.source))
  )

  // When paused, freeze the displayed entries so they don't scroll away
  const [frozenEntries, setFrozenEntries] = useState<DebugEntry[]>([])
  useEffect(() => {
    if (!paused) setFrozenEntries([])
  }, [paused])

  const displayedAll = paused && frozenEntries.length > 0 ? frozenEntries : entries
  const visibleEntries = showAll ? displayedAll : displayedAll.slice(-PAGE_SIZE)
  const hiddenCount = displayedAll.length - visibleEntries.length

  // Auto-scroll to bottom on new entries (only when not paused and not showing all)
  useEffect(() => {
    if (open && !paused && !showAll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [entries.length, open, paused, showAll])

  const toggleEnabled = () => {
    const next = !enabled
    setEnabled(next)
    setOpen(next)
    try { localStorage.setItem(LS_KEY, String(next)) } catch { /* ignore */ }
  }

  const toggleOpen = () => setOpen(o => !o)

  const togglePause = async () => {
    const next = !paused
    if (next) {
      // Freeze current entries before pausing
      setFrozenEntries(entries)
    }
    setPaused(next)
    await postPause(gameId, next)
  }

  return (
    <div className={`debug-panel-container ${open ? 'debug-panel-open' : ''}`}>
      {/* Toggle button — always visible */}
      <button
        className={`debug-panel-toggle-btn ${enabled ? 'debug-panel-toggle-active' : ''}`}
        onClick={enabled ? toggleOpen : toggleEnabled}
        title={enabled ? (open ? 'Collapse debug panel' : 'Expand debug panel') : 'Enable debug panel'}
      >
        🔍 Debug {enabled ? (open ? '▼' : '▶') : '(off)'}
      </button>

      {/* Side panel */}
      {open && (
        <div className="debug-panel">
          {/* Header */}
          <div className="debug-panel-header">
            <span>Debug Panel</span>
            <div className="debug-panel-header-actions">
              {enabled && !isGameOver && (
                <button
                  className={`debug-panel-pause-btn ${paused ? 'debug-panel-paused' : ''}`}
                  onClick={togglePause}
                  title={paused ? 'Resume game' : 'Pause game'}
                >
                  {paused ? '▶ Resume' : '⏸ Pause'}
                </button>
              )}
              {enabled && (
                <button className="debug-panel-disable-btn" onClick={toggleEnabled} title="Disable debug panel">
                  Disable
                </button>
              )}
              <button className="debug-panel-close-btn" onClick={toggleOpen} title="Close panel">
                ✕
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="debug-panel-body" ref={scrollRef}>
            {!enabled ? (
              <div className="debug-empty-state">
                Debug panel off — click to enable
              </div>
            ) : isLoading ? (
              <div className="debug-empty-state">Loading debug data…</div>
            ) : entries.length === 0 ? (
              <div className="debug-empty-state">
                No debug data for this game.
                <br />
                <small>Run with <code>--debug</code> to capture AI prompts and commentary.</small>
              </div>
            ) : (
              <>
                {hiddenCount > 0 && (
                  <button className="debug-show-all-btn" onClick={() => setShowAll(true)}>
                    ↑ Show {hiddenCount} earlier {hiddenCount === 1 ? 'entry' : 'entries'}
                  </button>
                )}
                {showAll && (
                  <button className="debug-show-all-btn" onClick={() => setShowAll(false)}>
                    ↑ Show latest {PAGE_SIZE} only
                  </button>
                )}
                {visibleEntries.map((entry: DebugEntry) =>
                  entry.entry_type === 'commentary' ? (
                    <CommentaryBlock key={entry.entry_id} entry={entry} />
                  ) : (
                    <PromptResponseBlock key={entry.entry_id} entry={entry} allSources={allSources} />
                  )
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
