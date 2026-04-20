import { useState, useRef, useEffect, useCallback } from 'react'
import type { DebugEntry } from '../types/debug'

// Left-border colors keyed by source name (cycles through defaults for unknown sources)
const SOURCE_COLORS: Record<string, string> = {
  default0: '#4a9eff',   // blue — Player 1
  default1: '#4caf50',   // green — Player 2
}

function getSourceColor(source: string, allSources: string[]): string {
  const idx = allSources.indexOf(source)
  if (idx === 0) return SOURCE_COLORS.default0
  if (idx === 1) return SOURCE_COLORS.default1
  // Additional players get a purple hue
  return `hsl(${(idx * 80 + 200) % 360}, 60%, 60%)`
}

interface Props {
  entry: DebugEntry
  allSources: string[]
  gameId: string
}

export function PromptResponseBlock({ entry, allSources, gameId }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const responseRef = useRef<HTMLDivElement>(null)
  const borderColor = getSourceColor(entry.source, allSources)

  // Annotation
  const [annotating, setAnnotating] = useState(false)
  const [annotationDraft, setAnnotationDraft] = useState('')
  const [annotationLoading, setAnnotationLoading] = useState(false)

  // Auto-scroll response box as new tokens arrive
  useEffect(() => {
    if (!collapsed && responseRef.current) {
      responseRef.current.scrollTop = responseRef.current.scrollHeight
    }
  }, [entry.response, collapsed])

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

  return (
    <div className="debug-block" style={{ borderLeftColor: borderColor }}>
      {/* Header */}
      <div className="debug-block-header" onClick={() => setCollapsed(c => !c)}>
        <span className="debug-block-chevron">{collapsed ? '▶' : '▼'}</span>
        <span className="debug-block-source">{entry.source}</span>
        <span className="debug-block-badge">
          Turn {entry.turn} / {entry.phase} / {entry.step}
        </span>
        <span className="debug-block-type">Prompt+Response</span>
        {!entry.is_complete && <span className="debug-block-streaming">⟳ streaming</span>}
      </div>

      {/* Body */}
      {!collapsed && (
        <div className="debug-block-body">
          <div className="debug-block-section-label">Prompt</div>
          <pre className="debug-block-pre debug-block-prompt">{entry.prompt}</pre>

          <div className="debug-block-section-label">Response</div>
          <div
            ref={responseRef}
            className="debug-block-pre debug-block-response"
          >
            {entry.response || <span className="debug-muted">(waiting…)</span>}
            {!entry.is_complete && <span className="debug-cursor">▋</span>}
          </div>

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
