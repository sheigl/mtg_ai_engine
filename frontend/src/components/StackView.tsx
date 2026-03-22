import type { StackObject } from '../types/game'
import '../styles/board.css'

interface StackViewProps {
  stack: StackObject[]
}

export function StackView({ stack }: StackViewProps) {
  if (stack.length === 0) {
    return <span className="stack-empty">Stack empty</span>
  }

  return (
    <div className="stack-view">
      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
        Stack ({stack.length}):
      </span>
      {stack.map((obj) => (
        <div key={obj.id} className="stack-item">
          <span className="stack-item-name">{obj.source_card.name}</span>
          <span className="stack-item-controller"> ({obj.controller})</span>
          {obj.targets.length > 0 && (
            <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>
              {' '}→ {obj.targets.length} target{obj.targets.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
      ))}
    </div>
  )
}
