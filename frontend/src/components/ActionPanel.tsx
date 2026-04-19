import type { LegalAction } from '../hooks/useLegalActions'
import type { Step } from '../types/game'

interface ActionPanelProps {
  isMyTurn: boolean
  phase: string | null
  step: Step | null
  legalActions: LegalAction[]
  selectedAttackers: Set<string>
  hasBlockerAssignments: boolean
  autoPassPriority: boolean
  isPending: boolean
  lastError: string | null
  isResponseWindow: boolean
  onPassPriority: () => void
  onConfirmAttackers: () => void
  onConfirmBlockers: () => void
  onToggleAutoPass: () => void
  onClearError: () => void
}

export function ActionPanel({
  isMyTurn,
  phase: _phase,
  step,
  legalActions,
  selectedAttackers,
  hasBlockerAssignments,
  autoPassPriority,
  isPending,
  lastError,
  isResponseWindow,
  onPassPriority,
  onConfirmAttackers,
  onConfirmBlockers,
  onToggleAutoPass,
  onClearError,
}: ActionPanelProps) {
  if (!isMyTurn) return null

  const isDeclareAttackers = step === 'declare_attackers'
  const isDeclareBlockers = step === 'declare_blockers'
  const canPass = legalActions.some(a => a.action_type === 'pass')

  return (
    <div style={{
      position: 'fixed',
      bottom: '1rem',
      left: '50%',
      transform: 'translateX(-50%)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: '0.5rem',
      zIndex: 100,
      pointerEvents: 'none',
    }}>
      {/* Turn indicator */}
      <div style={{
        background: isResponseWindow ? 'rgba(255,200,0,0.15)' : 'rgba(88,166,255,0.15)',
        border: `1px solid ${isResponseWindow ? '#ffc800' : 'var(--active-glow)'}`,
        borderRadius: '6px',
        padding: '0.3rem 0.8rem',
        fontSize: '0.75rem',
        fontWeight: 600,
        color: isResponseWindow ? '#ffc800' : 'var(--active-glow)',
        pointerEvents: 'none',
      }}>
        {isResponseWindow ? 'Response Window — Opponent is casting' : 'Your Turn'}
      </div>

      {/* Error */}
      {lastError && (
        <div style={{
          background: 'rgba(220,50,50,0.2)',
          border: '1px solid #dc3232',
          borderRadius: '6px',
          padding: '0.3rem 0.8rem',
          fontSize: '0.75rem',
          color: '#ff6b6b',
          display: 'flex',
          gap: '0.5rem',
          alignItems: 'center',
          pointerEvents: 'all',
        }}>
          {lastError}
          <button onClick={onClearError} style={{ background: 'none', border: 'none', color: '#ff6b6b', cursor: 'pointer', padding: 0, fontSize: '0.8rem' }}>✕</button>
        </div>
      )}

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: '0.5rem', pointerEvents: 'all' }}>
        {isDeclareAttackers && selectedAttackers.size > 0 && (
          <button
            onClick={onConfirmAttackers}
            disabled={isPending}
            style={btnStyle('#e55', '#fff')}
          >
            {isPending ? '…' : `Attack with ${selectedAttackers.size}`}
          </button>
        )}
        {isDeclareBlockers && hasBlockerAssignments && (
          <button
            onClick={onConfirmBlockers}
            disabled={isPending}
            style={btnStyle('#4a9', '#fff')}
          >
            {isPending ? '…' : 'Confirm Blocks'}
          </button>
        )}
        {canPass && (
          <button
            onClick={onPassPriority}
            disabled={isPending}
            style={btnStyle('var(--bg-secondary)', 'var(--text-secondary)', '1px solid var(--border-default)')}
          >
            {isPending ? '…' : isDeclareAttackers ? 'No Attacks' : isDeclareBlockers ? 'No Blocks' : 'Pass Priority'}
          </button>
        )}
      </div>

      {/* Auto-pass toggle */}
      <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.7rem', color: 'var(--text-muted)', cursor: 'pointer', pointerEvents: 'all' }}>
        <input
          type="checkbox"
          checked={autoPassPriority}
          onChange={onToggleAutoPass}
          style={{ cursor: 'pointer' }}
        />
        Auto-pass when no actions available
      </label>
    </div>
  )
}

function btnStyle(bg: string, color: string, border = 'none') {
  return {
    background: bg,
    color,
    border,
    borderRadius: '6px',
    padding: '0.5rem 1.2rem',
    fontSize: '0.85rem',
    fontWeight: 700,
    cursor: 'pointer',
    transition: 'opacity 0.15s',
  } as const
}
