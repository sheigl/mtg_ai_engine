import { useEffect, useRef, useState } from 'react'
import { useDebugLog } from '../hooks/useDebugLog'
import { PromptResponseBlock } from './PromptResponseBlock'
import { CommentaryBlock } from './CommentaryBlock'
import type { DebugEntry } from '../types/debug'
import '../styles/debug.css'

const PAGE_SIZE = 10

interface Props {
  gameId: string
  isGameOver: boolean
  debugEnabled?: boolean
}

async function postPause(gameId: string, paused: boolean) {
  await fetch(`/game/${gameId}/${paused ? 'pause' : 'resume'}`, { method: 'POST' })
}

export function DebugPanel({ gameId, isGameOver }: Props) {
  const [open, setOpen] = useState(true)
  const [showAll, setShowAll] = useState(false)
  const [paused, setPaused] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const { entries, isLoading } = useDebugLog(gameId, true, isGameOver)

  const allSources = Array.from(
    new Set(entries.filter(e => e.source !== 'Observer AI').map(e => e.source))
  )

  const [frozenEntries, setFrozenEntries] = useState<DebugEntry[]>([])
  useEffect(() => {
    if (!paused) setFrozenEntries([])
  }, [paused])

  const displayedAll = paused && frozenEntries.length > 0 ? frozenEntries : entries
  const visibleEntries = showAll ? displayedAll : displayedAll.slice(-PAGE_SIZE)
  const hiddenCount = displayedAll.length - visibleEntries.length

  useEffect(() => {
    if (open && !paused && !showAll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [entries.length, open, paused, showAll])

  const togglePause = async () => {
    const next = !paused
    if (next) setFrozenEntries(entries)
    setPaused(next)
    await postPause(gameId, next)
  }

  return (
    <div className={`debug-panel-container ${open ? 'debug-panel-open' : ''}`}>
      <button
        className="debug-panel-toggle-btn debug-panel-toggle-active"
        onClick={() => setOpen(o => !o)}
        title={open ? 'Collapse debug panel' : 'Expand debug panel'}
      >
        🔍 AI {open ? '▼' : '▶'}
      </button>

      {open && (
        <div className="debug-panel">
          <div className="debug-panel-header">
            <span>AI Commentary</span>
            <div className="debug-panel-header-actions">
              {!isGameOver && (
                <button
                  className={`debug-panel-pause-btn ${paused ? 'debug-panel-paused' : ''}`}
                  onClick={togglePause}
                  title={paused ? 'Resume game' : 'Pause game'}
                >
                  {paused ? '▶ Resume' : '⏸ Pause'}
                </button>
              )}
              <button className="debug-panel-close-btn" onClick={() => setOpen(false)} title="Collapse panel">
                ✕
              </button>
            </div>
          </div>

          <div className="debug-panel-body" ref={scrollRef}>
            {isLoading ? (
              <div className="debug-empty-state">Loading…</div>
            ) : entries.length === 0 ? (
              <div className="debug-empty-state">
                No AI entries yet.
                <br />
                <small>
                  Heuristic players don't generate LLM entries.
                  Add an <strong>observer URL</strong> when creating the game to see move commentary.
                </small>
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
                    <CommentaryBlock key={entry.entry_id} entry={entry} gameId={gameId} />
                  ) : (
                    <PromptResponseBlock key={entry.entry_id} entry={entry} allSources={allSources} gameId={gameId} />
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
