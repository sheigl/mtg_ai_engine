import { useState } from 'react'
import type { LegalAction } from '../hooks/useLegalActions'
import type { Card } from '../types/game'

interface TargetChoiceModalProps {
  action: LegalAction
  cardName: string
  targetNames?: Map<string, string>
  onConfirm: (target: string, xValue?: number) => void
  onCancel: () => void
}

export function TargetChoiceModal({ action, cardName, targetNames, onConfirm, onCancel }: TargetChoiceModalProps) {
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null)
  const [xValue, setXValue] = useState(0)
  const targets = action.valid_targets ?? []
  const needsX = action.x_value !== undefined && action.x_value !== null

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: '0.5rem' }}>
          Cast {cardName}
        </div>

        {targets.length > 0 && (
          <>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              Choose a target:
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', maxHeight: '200px', overflowY: 'auto', marginBottom: '0.75rem' }}>
              {targets.map(t => (
                <button
                  key={t}
                  onClick={() => setSelectedTarget(t)}
                  style={{
                    background: selectedTarget === t ? 'var(--active-glow)' : 'var(--bg-tertiary)',
                    color: selectedTarget === t ? '#000' : 'var(--text-primary)',
                    border: '1px solid var(--border-default)',
                    borderRadius: '4px',
                    padding: '0.4rem 0.75rem',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    textAlign: 'left',
                  }}
                >
                  {targetNames?.get(t) ?? t}
                </button>
              ))}
            </div>
          </>
        )}

        {needsX && (
          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              X value:{' '}
              <input
                type="number"
                min={0}
                value={xValue}
                onChange={e => setXValue(parseInt(e.target.value, 10) || 0)}
                style={{ width: '60px', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border-muted)', borderRadius: '4px', padding: '0.1rem 0.3rem', fontSize: '0.8rem' }}
              />
            </label>
          </div>
        )}

        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
          <button onClick={onCancel} style={cancelBtnStyle}>Cancel</button>
          <button
            onClick={() => {
              const t = targets.length > 0 ? (selectedTarget ?? targets[0]) : ''
              onConfirm(t, needsX ? xValue : undefined)
            }}
            disabled={targets.length > 0 && !selectedTarget}
            style={confirmBtnStyle}
          >
            Cast
          </button>
        </div>
      </div>
    </div>
  )
}

interface MulliganModalProps {
  onKeep: () => void
  onMulligan: () => void
  hand: Card[]
}

export function MulliganModal({ onKeep, onMulligan, hand }: MulliganModalProps) {
  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: '0.5rem' }}>
          Keep this hand? ({hand.length} cards)
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
          {hand.map(c => c.name).join(', ')}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
          <button onClick={onMulligan} style={cancelBtnStyle}>Mulligan</button>
          <button onClick={onKeep} style={confirmBtnStyle}>Keep</button>
        </div>
      </div>
    </div>
  )
}

interface ScryModalProps {
  topCards: string[]
  onChoice: (keepOnTop: boolean) => void
}

export function ScryModal({ topCards, onChoice }: ScryModalProps) {
  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: '0.5rem' }}>
          Scry {topCards.length}
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
          The top card{topCards.length > 1 ? 's' : ''} of your library:
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', marginBottom: '0.75rem', maxHeight: '160px', overflowY: 'auto' }}>
          {topCards.map((name, i) => (
            <div key={i} style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-default)', borderRadius: '4px', padding: '0.3rem 0.6rem', fontSize: '0.85rem', color: 'var(--text-primary)' }}>
              {name}
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
          <button onClick={() => onChoice(false)} style={cancelBtnStyle}>Put on Bottom</button>
          <button onClick={() => onChoice(true)} style={confirmBtnStyle}>Keep on Top</button>
        </div>
      </div>
    </div>
  )
}

interface DiscardModalProps {
  hand: Card[]
  count: number
  onDiscard: (cardId: string) => void
}

export function DiscardModal({ hand, count, onDiscard }: DiscardModalProps) {
  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: '0.5rem' }}>
          Discard {count} card{count > 1 ? 's' : ''}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', maxHeight: '200px', overflowY: 'auto' }}>
          {hand.map(card => (
            <button
              key={card.id}
              onClick={() => onDiscard(card.id)}
              style={{
                background: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-default)',
                borderRadius: '4px',
                padding: '0.4rem 0.75rem',
                cursor: 'pointer',
                fontSize: '0.8rem',
                textAlign: 'left',
              }}
            >
              {card.name}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Shared styles ──────────────────────────────────────────────────────────────

const overlayStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,0.7)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 200,
}

const modalStyle: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--active-glow)',
  borderRadius: '10px',
  padding: '1.25rem',
  minWidth: '280px',
  maxWidth: '420px',
  boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
}

const confirmBtnStyle: React.CSSProperties = {
  background: 'var(--active-glow)',
  color: '#000',
  border: 'none',
  borderRadius: '6px',
  padding: '0.4rem 1rem',
  fontWeight: 700,
  cursor: 'pointer',
  fontSize: '0.85rem',
}

const cancelBtnStyle: React.CSSProperties = {
  background: 'var(--bg-tertiary)',
  color: 'var(--text-secondary)',
  border: '1px solid var(--border-muted)',
  borderRadius: '6px',
  padding: '0.4rem 1rem',
  cursor: 'pointer',
  fontSize: '0.85rem',
}
