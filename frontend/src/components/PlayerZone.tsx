import type { PlayerState } from '../types/game'
import '../styles/board.css'

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

export function PlayerZone({ player, isActive, isOpponent = false, format, commanderDamage }: PlayerZoneProps) {
  const startingLife = format === 'commander' ? 40 : 20
  const isCommander = format === 'commander'

  return (
    <div className={`player-info${isActive ? ' active' : ''}${isOpponent ? ' opponent' : ''}`}>
      <span className="player-name">{player.name}</span>
      <span className={`player-life ${lifeClass(player.life, startingLife)}`}>
        {player.life}
      </span>

      <div className="zone-counts">
        <span className="zone-count">
          <span className="zone-label">Hand</span> {player.hand.length}
        </span>
        <span className="zone-count">
          <span className="zone-label">Library</span> {player.library.length}
        </span>
        <span className="zone-count">
          <span className="zone-label">Grave</span> {player.graveyard.length}
        </span>
        {player.exile.length > 0 && (
          <span className="zone-count">
            <span className="zone-label">Exile</span> {player.exile.length}
          </span>
        )}
        {player.poison_counters > 0 && (
          <span className="zone-count" style={{ color: 'var(--life-low)' }}>
            <span className="zone-label">Poison</span> {player.poison_counters}
          </span>
        )}
      </div>

      {isCommander && player.command_zone.length > 0 && (
        <div className="commander-zone">
          <span className="zone-label">CMD:</span>
          {player.command_zone.map(c => (
            <span key={c.id}>{c.name}</span>
          ))}
          {player.commander_cast_count > 0 && (
            <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>
              (tax: {player.commander_cast_count * 2})
            </span>
          )}
        </div>
      )}

      {isCommander && commanderDamage && Object.keys(commanderDamage).length > 0 && (
        <div className="commander-damage">
          {Object.entries(commanderDamage).map(([source, dmg]) => (
            dmg > 0 && <span key={source}>CMD DMG from {source}: {dmg}</span>
          ))}
        </div>
      )}
    </div>
  )
}
