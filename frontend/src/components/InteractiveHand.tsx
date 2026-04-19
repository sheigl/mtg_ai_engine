import type { Card } from '../types/game'
import type { LegalAction } from '../hooks/useLegalActions'
import { CardView } from './CardView'

interface InteractiveHandProps {
  hand: Card[]
  legalActionsByCard: Map<string, LegalAction[]>
  isPending: boolean
  onPlayLand: (cardId: string) => void
  onCastSpell: (action: LegalAction, cardId: string) => void
  onDragStart?: (cardId: string) => void
  onDragEnd?: () => void
}

export function InteractiveHand({
  hand,
  legalActionsByCard,
  isPending,
  onPlayLand,
  onCastSpell,
  onDragStart,
  onDragEnd,
}: InteractiveHandProps) {
  if (hand.length === 0) {
    return (
      <div style={{
        padding: '0.5rem',
        color: 'var(--text-muted)',
        fontSize: '0.75rem',
        textAlign: 'center',
      }}>
        Empty hand
      </div>
    )
  }

  return (
    <div>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', padding: '0.25rem 0.5rem' }}>
        Click or drag playable cards (highlighted) to play them
      </div>
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0.5rem',
        padding: '0.5rem',
      }}>
        {hand.map(card => {
          const actions = legalActionsByCard.get(card.id) ?? []
          const playLandAction = actions.find(a => a.action_type === 'play_land')
          const castAction = actions.find(a => a.action_type === 'cast')
          const isPlayable = !!(playLandAction || castAction)

          function handleClick() {
            if (isPending || !isPlayable) return
            if (playLandAction) {
              onPlayLand(card.id)
            } else if (castAction) {
              onCastSpell(castAction, card.id)
            }
          }

          return (
            <div
              key={card.id}
              onClick={handleClick}
              draggable={isPlayable && !isPending}
              onDragStart={isPlayable && !isPending ? (e) => {
                e.dataTransfer.setData('text/plain', card.id)
                e.dataTransfer.effectAllowed = 'move'
                onDragStart?.(card.id)
              } : undefined}
              onDragEnd={onDragEnd}
              title={isPlayable ? (playLandAction ? 'Click or drag to play land' : 'Click or drag to cast') : card.name}
              style={{
                cursor: isPlayable && !isPending ? 'grab' : 'default',
                opacity: isPending ? 0.6 : 1,
                borderRadius: '6px',
                outline: isPlayable ? '2px solid var(--active-glow)' : '2px solid transparent',
                outlineOffset: '2px',
                boxShadow: isPlayable ? '0 0 8px rgba(88,166,255,0.4)' : 'none',
                transition: 'outline-color 0.15s, box-shadow 0.15s',
                position: 'relative',
              }}
            >
              <CardView card={card} />
              {isPlayable && (
                <div style={{
                  position: 'absolute',
                  bottom: '2px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  background: 'var(--active-glow)',
                  color: '#000',
                  fontSize: '0.6rem',
                  fontWeight: 700,
                  borderRadius: '3px',
                  padding: '1px 4px',
                  whiteSpace: 'nowrap',
                }}>
                  {playLandAction ? 'PLAY' : 'CAST'}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
