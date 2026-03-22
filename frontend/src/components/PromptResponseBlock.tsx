import { useState, useRef, useEffect } from 'react'
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
}

export function PromptResponseBlock({ entry, allSources }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const responseRef = useRef<HTMLDivElement>(null)
  const borderColor = getSourceColor(entry.source, allSources)

  // Auto-scroll response box as new tokens arrive
  useEffect(() => {
    if (!collapsed && responseRef.current) {
      responseRef.current.scrollTop = responseRef.current.scrollHeight
    }
  }, [entry.response, collapsed])

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
        </div>
      )}
    </div>
  )
}
