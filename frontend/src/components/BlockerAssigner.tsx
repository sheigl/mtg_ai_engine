import type { Permanent } from '../types/game'

interface BlockerAssignerProps {
  myCreatures: Permanent[]
  attackingCreatures: Permanent[]
  assignments: Map<string, string>
  legalBlockerIds: Set<string>
  isPending: boolean
  onAssign: (blockerId: string, attackerId: string) => void
  onUnassign: (blockerId: string) => void
}

export function BlockerAssigner({
  myCreatures,
  attackingCreatures,
  assignments,
  legalBlockerIds,
  isPending,
  onAssign,
  onUnassign,
}: BlockerAssignerProps) {
  const blockableCreatures = myCreatures.filter(p => legalBlockerIds.has(p.id))

  if (attackingCreatures.length === 0) return null

  return (
    <div style={{
      background: 'rgba(74,154,100,0.1)',
      border: '1px solid rgba(74,154,100,0.4)',
      borderRadius: '8px',
      padding: '0.75rem',
      marginTop: '0.5rem',
    }}>
      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#4a9a64', marginBottom: '0.5rem' }}>
        Assign Blockers
      </div>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        {attackingCreatures.map(attacker => {
          const myBlocker = Array.from(assignments.entries()).find(([, aid]) => aid === attacker.id)
          return (
            <div key={attacker.id} style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-default)',
              borderRadius: '6px',
              padding: '0.5rem',
              minWidth: '120px',
            }}>
              <div style={{ fontSize: '0.7rem', color: '#e55', fontWeight: 600, marginBottom: '0.25rem' }}>
                Attacker: {attacker.card.name}
              </div>
              {myBlocker ? (
                <div style={{ fontSize: '0.7rem', color: '#4a9a64' }}>
                  Blocked by: {myCreatures.find(c => c.id === myBlocker[0])?.card.name}
                  <button
                    onClick={() => !isPending && onUnassign(myBlocker[0])}
                    style={{ background: 'none', border: 'none', color: '#e55', cursor: 'pointer', marginLeft: '0.25rem', fontSize: '0.7rem' }}
                  >
                    ✕
                  </button>
                </div>
              ) : (
                <select
                  onChange={e => {
                    if (e.target.value && !isPending) {
                      onAssign(e.target.value, attacker.id)
                      e.target.value = ''
                    }
                  }}
                  defaultValue=""
                  disabled={isPending}
                  style={{ fontSize: '0.7rem', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border-muted)', borderRadius: '4px', padding: '0.1rem 0.3rem', width: '100%' }}
                >
                  <option value="">— No blocker —</option>
                  {blockableCreatures
                    .filter(c => !assignments.has(c.id))
                    .map(c => (
                      <option key={c.id} value={c.id}>{c.card.name}</option>
                    ))}
                </select>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
