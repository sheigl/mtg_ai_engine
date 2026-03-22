import { useState } from 'react'
import type { DebugEntry, Rating } from '../types/debug'

const RATING_BADGE: Record<Rating, { emoji: string; color: string; label: string }> = {
  good:       { emoji: '🟢', color: '#4caf50', label: 'Good' },
  acceptable: { emoji: '🟡', color: '#ffc107', label: 'Acceptable' },
  suboptimal: { emoji: '🔴', color: '#f44336', label: 'Suboptimal' },
}

interface Props {
  entry: DebugEntry
}

export function CommentaryBlock({ entry }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const rating = entry.rating as Rating | undefined
  const badge = rating ? RATING_BADGE[rating] : null

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
      </div>

      {/* Body */}
      {!collapsed && (
        <div className="debug-block-body">
          <div className="debug-block-section-label">Commentary</div>
          <div className="debug-block-commentary">
            {entry.explanation || entry.response || <span className="debug-muted">No analysis.</span>}
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
