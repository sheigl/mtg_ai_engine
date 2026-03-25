import { useRef, useEffect, useState, useCallback } from 'react'
import type { DebugEntry, Rating } from '../types/debug'

const RATING_BADGE: Record<Rating, { emoji: string; color: string; label: string }> = {
  good:       { emoji: '🟢', color: '#4caf50', label: 'Good' },
  acceptable: { emoji: '🟡', color: '#ffc107', label: 'Acceptable' },
  suboptimal: { emoji: '🔴', color: '#f44336', label: 'Suboptimal' },
}

interface Props {
  entry: DebugEntry
  gameId: string
}

export function CommentaryBlock({ entry, gameId }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const [thinkingExpanded, setThinkingExpanded] = useState(false)
  const [skipping, setSkipping] = useState(false)
  const thinkingRef = useRef<HTMLDivElement>(null)
  const rating = entry.rating as Rating | undefined
  const badge = rating ? RATING_BADGE[rating] : null
  const hasThinking = !!(entry.thinking)
  const displayText = entry.explanation || entry.response

  const handleSkip = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation()
    setSkipping(true)
    try {
      await fetch(`/game/${gameId}/debug/entry/${entry.entry_id}/skip`, { method: 'POST' })
    } finally {
      setSkipping(false)
    }
  }, [gameId, entry.entry_id])

  // Auto-scroll thinking box as tokens arrive
  useEffect(() => {
    if (thinkingExpanded && thinkingRef.current) {
      thinkingRef.current.scrollTop = thinkingRef.current.scrollHeight
    }
  }, [entry.thinking, thinkingExpanded])

  return (
    <div className="debug-block debug-block-observer">
      {/* Header */}
      <div className="debug-block-header" onClick={() => setCollapsed(c => !c)}>
        <span className="debug-block-chevron">{collapsed ? '▶' : '▼'}</span>
        <span className="debug-block-source">Observer AI</span>
        <span className="debug-block-badge">
          Turn {entry.turn} / {entry.phase} / {entry.step}
        </span>
        {badge && (
          <span className="debug-rating-badge" style={{ color: badge.color }}>
            {badge.emoji} {badge.label}
          </span>
        )}
        {!entry.is_complete && <span className="debug-block-streaming">⟳ streaming</span>}
        {!entry.is_complete && (
          <button
            className="debug-skip-btn"
            onClick={handleSkip}
            disabled={skipping}
            title="Skip observer analysis and continue game"
          >
            {skipping ? '…' : 'Skip'}
          </button>
        )}
      </div>

      {/* Body */}
      {!collapsed && (
        <div className="debug-block-body">
          {/* Thinking block — collapsible, shown when model has reasoning tokens */}
          {hasThinking && (
            <div className="debug-thinking-container">
              <div
                className="debug-thinking-header"
                onClick={() => setThinkingExpanded(e => !e)}
              >
                <span>{thinkingExpanded ? '▼' : '▶'}</span>
                <span className="debug-thinking-label">
                  {!entry.is_complete && !thinkingExpanded ? '⟳ thinking…' : 'Thinking'}
                </span>
              </div>
              {thinkingExpanded && (
                <div ref={thinkingRef} className="debug-thinking-body">
                  {entry.thinking}
                  {!entry.is_complete && <span className="debug-cursor">▋</span>}
                </div>
              )}
            </div>
          )}

          <div className="debug-block-section-label">Commentary</div>
          <div className="debug-block-commentary">
            {displayText
              ? <>{displayText}{!entry.is_complete && <span className="debug-cursor">▋</span>}</>
              : !entry.is_complete
                ? <span className="debug-muted">thinking…</span>
                : <span className="debug-muted">No analysis.</span>
            }
          </div>

          {entry.alternative && (
            <div className="debug-better-play">
              <span className="debug-better-play-label">💡 Better play:</span>
              <span className="debug-better-play-text">{entry.alternative}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
