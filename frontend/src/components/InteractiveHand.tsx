import { useRef, useState } from 'react'
import type { Card } from '../types/game'
import type { LegalAction } from '../hooks/useLegalActions'
import { CardView } from './CardView'

interface InteractiveHandProps {
  hand: Card[]
  legalActionsByCard: Map<string, LegalAction[]>
  isPending: boolean
  handOrder: string[]
  onReorder: (newOrder: string[]) => void
  onPlayLand: (cardId: string) => void
  onCastSpell: (action: LegalAction, cardId: string) => void
  onDragStart?: (cardId: string) => void
  onDragEnd?: () => void
}

export function InteractiveHand({
  hand,
  legalActionsByCard,
  isPending,
  handOrder,
  onReorder,
  onPlayLand,
  onCastSpell,
  onDragStart,
  onDragEnd,
}: InteractiveHandProps) {
  const reorderDragCardId = useRef<string | null>(null)
  const [dragOverCardId, setDragOverCardId] = useState<string | null>(null)

  // Sort cards by handOrder
  const cardById = new Map(hand.map(c => [c.id, c]))
  const sortedHand = [
    ...handOrder.filter(id => cardById.has(id)).map(id => cardById.get(id)!),
    ...hand.filter(c => !handOrder.includes(c.id)),
  ]

  if (sortedHand.length === 0) {
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

  function handleReorderDrop(e: React.DragEvent, targetCardId: string) {
    const dragId = e.dataTransfer.getData('reorder-hand')
    if (!dragId || dragId === targetCardId) {
      setDragOverCardId(null)
      return
    }
    const order = handOrder.filter(id => cardById.has(id))
    const fromIdx = order.indexOf(dragId)
    const toIdx = order.indexOf(targetCardId)
    if (fromIdx === -1 || toIdx === -1) {
      setDragOverCardId(null)
      return
    }
    const next = [...order]
    next.splice(fromIdx, 1)
    next.splice(toIdx, 0, dragId)
    onReorder(next)
    setDragOverCardId(null)
  }

  return (
    <div>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', padding: '0.25rem 0.5rem' }}>
        Click or drag playable cards (highlighted) to play them. Drag any card within hand to reorder.
      </div>
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0.5rem',
        padding: '0.5rem',
      }}>
        {sortedHand.map(card => {
          const actions = legalActionsByCard.get(card.id) ?? []
          const playLandAction = actions.find(a => a.action_type === 'play_land')
          const castAction = actions.find(a => a.action_type === 'cast')
          const isPlayable = !!(playLandAction || castAction)
          const isReorderTarget = dragOverCardId === card.id

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
              draggable={!isPending}
              onDragStart={(e) => {
                reorderDragCardId.current = card.id
                e.dataTransfer.setData('reorder-hand', card.id)
                if (isPlayable) {
                  e.dataTransfer.setData('text/plain', card.id)
                  e.dataTransfer.effectAllowed = 'move'
                  onDragStart?.(card.id)
                }
              }}
              onDragOver={(e) => {
                if (reorderDragCardId.current && reorderDragCardId.current !== card.id) {
                  e.preventDefault()
                  e.stopPropagation()
                  setDragOverCardId(card.id)
                }
              }}
              onDragLeave={() => {
                if (dragOverCardId === card.id) setDragOverCardId(null)
              }}
              onDrop={(e) => {
                // Only handle reorder drops within the hand
                if (e.dataTransfer.getData('reorder-hand')) {
                  e.preventDefault()
                  e.stopPropagation()
                  handleReorderDrop(e, card.id)
                }
              }}
              onDragEnd={() => {
                reorderDragCardId.current = null
                setDragOverCardId(null)
                onDragEnd?.()
              }}
              title={isPlayable ? (playLandAction ? 'Click or drag to play land' : 'Click or drag to cast') : `${card.name} (drag to reorder)`}
              style={{
                cursor: isPlayable && !isPending ? 'grab' : (!isPending ? 'grab' : 'default'),
                opacity: isPending ? 0.6 : 1,
                borderRadius: '6px',
                outline: isPlayable
                  ? '2px solid var(--active-glow)'
                  : isReorderTarget
                    ? '2px dashed #aaa'
                    : '2px solid transparent',
                outlineOffset: '2px',
                boxShadow: isPlayable ? '0 0 8px rgba(88,166,255,0.4)' : 'none',
                transition: 'outline-color 0.15s, box-shadow 0.15s',
                position: 'relative',
                transform: isReorderTarget ? 'scale(1.05)' : undefined,
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
