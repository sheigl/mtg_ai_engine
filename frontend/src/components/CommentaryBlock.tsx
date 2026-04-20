import { useRef, useEffect, useState, useCallback } from 'react'
import type { DebugEntry, Rating } from '../types/debug'

const RATING_BADGE: Record<Rating, { emoji: string; color: string; label: string }> = {
  good:       { emoji: '🟢', color: '#4caf50', label: 'Good' },
  acceptable: { emoji: '🟡', color: '#ffc107', label: 'Acceptable' },
  suboptimal: { emoji: '🔴', color: '#f44336', label: 'Suboptimal' },
}

const RATING_OPTIONS: Rating[] = ['good', 'acceptable', 'suboptimal']

interface Props {
  entry: DebugEntry
  gameId: string
}

export function CommentaryBlock({ entry, gameId }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const [thinkingExpanded, setThinkingExpanded] = useState(false)
  const [skipping, setSkipping] = useState(false)

  // Rating override
  const [ratingPickerOpen, setRatingPickerOpen] = useState(false)
  const [rerateLoading, setRerateLoading] = useState(false)

  // Annotation
  const [annotating, setAnnotating] = useState(false)
  const [annotationDraft, setAnnotationDraft] = useState('')
  const [annotationLoading, setAnnotationLoading] = useState(false)

  const thinkingRef = useRef<HTMLDivElement>(null)
  const rating = entry.rating as Rating | undefined
  const override = entry.player_rating_override as Rating | undefined | null
  const displayRating = override ?? rating
  const badge = displayRating ? RATING_BADGE[displayRating] : null
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

  const handleRerate = useCallback(async (newRating: Rating | null) => {
    setRatingPickerOpen(false)
    setRerateLoading(true)
    try {
      await fetch(`/game/${gameId}/debug/entry/${entry.entry_id}/rerate`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating: newRating }),
      })
    } finally {
      setRerateLoading(false)
    }
  }, [gameId, entry.entry_id])

  const handleAnnotationSave = useCallback(async () => {
    const text = annotationDraft.trim() || null
    setAnnotationLoading(true)
    try {
      await fetch(`/game/${gameId}/debug/entry/${entry.entry_id}/annotate`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      setAnnotating(false)
    } finally {
      setAnnotationLoading(false)
    }
  }, [gameId, entry.entry_id, annotationDraft])

  const handleAnnotationEdit = useCallback(() => {
    setAnnotationDraft(entry.player_annotation ?? '')
    setAnnotating(true)
  }, [entry.player_annotation])

  const handleAnnotationDelete = useCallback(async () => {
    setAnnotationLoading(true)
    try {
      await fetch(`/game/${gameId}/debug/entry/${entry.entry_id}/annotate`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: null }),
      })
    } finally {
      setAnnotationLoading(false)
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

        {/* Rating badge — clickable for override when complete */}
        {badge && entry.is_complete ? (
          <span className="debug-rating-badge-wrapper" onClick={e => { e.stopPropagation(); setRatingPickerOpen(o => !o) }}>
            <span
              className={`debug-rating-badge ${override ? 'debug-rating-badge-override' : ''}`}
              style={{ color: badge.color }}
              title={override ? `Override (original: ${rating})` : 'Click to override rating'}
            >
              {badge.emoji} {badge.label}
              {override && <span className="debug-rating-override-indicator"> ✏️</span>}
            </span>
            {rerateLoading && <span className="debug-muted"> …</span>}
          </span>
        ) : badge ? (
          <span className="debug-rating-badge" style={{ color: badge.color }}>
            {badge.emoji} {badge.label}
          </span>
        ) : null}

        {/* Rating override picker */}
        {ratingPickerOpen && (
          <div className="debug-rating-picker" onClick={e => e.stopPropagation()}>
            {RATING_OPTIONS.map(r => (
              <button
                key={r}
                className={`debug-rating-picker-option ${r === (override ?? rating) ? 'debug-rating-picker-active' : ''}`}
                style={{ color: RATING_BADGE[r].color }}
                onClick={() => handleRerate(r)}
              >
                {RATING_BADGE[r].emoji} {RATING_BADGE[r].label}
              </button>
            ))}
            {override && (
              <button className="debug-rating-picker-reset" onClick={() => handleRerate(null)}>
                Reset to AI
              </button>
            )}
          </div>
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
          {/* Overridden original rating dim display */}
          {override && rating && (
            <div className="debug-rating-original-dim">
              AI Rating: <span style={{ color: RATING_BADGE[rating as Rating].color }}>{RATING_BADGE[rating as Rating].emoji} {RATING_BADGE[rating as Rating].label}</span>
            </div>
          )}

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

          {/* Annotation section */}
          {entry.is_complete && (
            <div className="debug-annotation-section">
              {annotating ? (
                <div className="debug-annotation-editor">
                  <textarea
                    className="debug-annotation-textarea"
                    value={annotationDraft}
                    onChange={e => setAnnotationDraft(e.target.value)}
                    placeholder="Add your comment…"
                    rows={3}
                    autoFocus
                  />
                  <div className="debug-annotation-actions">
                    <button
                      className="debug-annotation-save-btn"
                      onClick={handleAnnotationSave}
                      disabled={annotationLoading || annotationDraft.trim() === entry.player_annotation}
                    >
                      {annotationLoading ? '…' : 'Save'}
                    </button>
                    <button
                      className="debug-annotation-cancel-btn"
                      onClick={() => setAnnotating(false)}
                      disabled={annotationLoading}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : entry.player_annotation ? (
                <div className="debug-annotation-display">
                  <span className="debug-annotation-label">💬 Your comment:</span>
                  <span className="debug-annotation-text">{entry.player_annotation}</span>
                  <div className="debug-annotation-controls">
                    <button className="debug-annotation-edit-btn" onClick={handleAnnotationEdit}>Edit</button>
                    <button className="debug-annotation-delete-btn" onClick={handleAnnotationDelete} disabled={annotationLoading}>
                      {annotationLoading ? '…' : 'Delete'}
                    </button>
                  </div>
                </div>
              ) : (
                <button className="debug-annotation-add-btn" onClick={() => { setAnnotationDraft(''); setAnnotating(true) }}>
                  + Add Comment
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
