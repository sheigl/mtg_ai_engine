import type { Permanent } from '../types/game'

interface AttackerSelectorProps {
  creatures: Permanent[]
  legalAttackerIds: Set<string>
  selectedAttackers: Set<string>
  isPending: boolean
  onToggle: (permanentId: string) => void
}

export function AttackerSelector({
  creatures,
  legalAttackerIds,
  selectedAttackers,
  isPending,
  onToggle,
}: AttackerSelectorProps) {
  const attackableCreatures = creatures.filter(
    p => !p.tapped && !p.summoning_sick && legalAttackerIds.has(p.id),
  )

  if (attackableCreatures.length === 0) return null

  return (
    <div style={{
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none',
      zIndex: 10,
    }}>
      {attackableCreatures.map(creature => (
        <div
          key={creature.id}
          onClick={() => !isPending && onToggle(creature.id)}
          style={{
            display: 'inline-block',
            cursor: isPending ? 'default' : 'pointer',
            pointerEvents: 'all',
          }}
        >
          <div style={{
            outline: selectedAttackers.has(creature.id) ? '3px solid #e55' : '2px dashed rgba(229,85,85,0.5)',
            outlineOffset: '2px',
            borderRadius: '4px',
            boxShadow: selectedAttackers.has(creature.id) ? '0 0 10px rgba(229,85,85,0.6)' : 'none',
          }}>
            <div style={{ fontSize: '0.65rem', color: '#e55', textAlign: 'center', fontWeight: 700 }}>
              {selectedAttackers.has(creature.id) ? '⚔ ATTACKING' : '⚔ ATTACK?'}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textAlign: 'center' }}>
              {creature.card.name}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
