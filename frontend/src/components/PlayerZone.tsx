import type { PlayerState } from '../types/game'

interface PlayerZoneProps {
  player: PlayerState
  isActive: boolean
  isOpponent?: boolean
  format?: string
  commanderDamage?: Record<string, number>
}

function lifeClass(life: number, startingLife: number): string {
  if (life > startingLife * 0.5) return 'high'
  if (life > startingLife * 0.25) return 'mid'
  return 'low'
}

function lifeColor(lifeClassName: string): string {
  if (lifeClassName === 'high') return 'var(--success)'
  if (lifeClassName === 'mid') return 'var(--warning)'
  return 'var(--danger)'
}

export function PlayerZone({ player, isActive, isOpponent = false, format, commanderDamage }: PlayerZoneProps) {
  const startingLife = format === 'commander' ? 40 : 20
  const isCommander = format === 'commander'
  const lClass = lifeClass(player.life, startingLife)
  const lColor = lifeColor(lClass)

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--space-4)',
      padding: 'var(--space-3) var(--space-4)',
      background: 'var(--surface-elevated)',
      borderRadius: 'var(--radius-lg)',
      border: `1px solid ${isActive ? 'var(--accent)' : 'var(--border-subtle)'}`,
      boxShadow: isActive ? 'var(--shadow-glow)' : 'var(--shadow-sm)',
      transition: 'all var(--transition-fast)',
      flexDirection: isOpponent ? 'row-reverse' : 'row',
    }}>
      {/* Name */}
      <span style={{
        fontWeight: 700,
        fontSize: 'var(--text-base)',
        color: 'var(--text-primary)',
        whiteSpace: 'nowrap',
      }}>
        {player.name}
      </span>

      {/* Life */}
      <span style={{
        fontSize: '1.75rem',
        fontWeight: 800,
        color: lColor,
        minWidth: '3rem',
        textAlign: 'center',
        lineHeight: 1,
        textShadow: `0 0 20px ${lColor}33`,
      }}>
        {player.life}
      </span>

      {/* Zone counts */}
      <div style={{
        display: 'flex',
        gap: 'var(--space-3)',
        fontSize: 'var(--text-xs)',
        color: 'var(--text-secondary)',
      }}>
        <ZoneCount label="Hand" count={player.hand.length} />
        <ZoneCount label="Deck" count={player.library.length} />
        <ZoneCount label="Grave" count={player.graveyard.length} />
        {player.exile.length > 0 && (
          <ZoneCount label="Exile" count={player.exile.length} />
        )}
        {player.poison_counters > 0 && (
          <ZoneCount label="Poison" count={player.poison_counters} color="var(--danger)" />
        )}
      </div>

      {/* Commander zone */}
      {isCommander && player.command_zone.length > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
          padding: 'var(--space-1) var(--space-2)',
          background: 'var(--surface-hover)',
          borderRadius: 'var(--radius-md)',
          fontSize: 'var(--text-xs)',
          border: '1px solid var(--border-subtle)',
        }}>
          <span style={{ color: 'var(--text-tertiary)', fontWeight: 600 }}>CMD</span>
          {player.command_zone.map(c => (
            <span key={c.id} style={{ color: 'var(--text-secondary)' }}>{c.name}</span>
          ))}
          {player.commander_cast_count > 0 && (
            <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>
              +{player.commander_cast_count * 2}
            </span>
          )}
        </div>
      )}

      {/* Commander damage */}
      {isCommander && commanderDamage && Object.keys(commanderDamage).length > 0 && (
        <div style={{
          display: 'flex',
          gap: 'var(--space-2)',
          fontSize: 'var(--text-xs)',
          color: 'var(--danger)',
        }}>
          {Object.entries(commanderDamage).map(([source, dmg]) => (
            dmg > 0 && (
              <span key={source} style={{
                padding: '2px 6px',
                background: 'var(--danger-subtle)',
                borderRadius: 'var(--radius-sm)',
                fontWeight: 600,
              }}>
                {source}: {dmg}
              </span>
            )
          ))}
        </div>
      )}
    </div>
  )
}

function ZoneCount({ label, count, color }: { label: string; count: number; color?: string }) {
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', color: color || 'inherit' }}>
      <span style={{ opacity: 0.6 }}>{label}</span>
      <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{count}</span>
    </span>
  )
}
