import { useEffect, useRef } from 'react'
import { useTranscript } from '../hooks/useTranscript'

interface ActionLogProps {
  gameId: string
}

const VISIBLE_EVENTS = new Set([
  'cast', 'resolve', 'zone_change', 'damage', 'attack', 'block',
  'life_change', 'game_end', 'trigger', 'activate', 'draw',
])

const EVENT_COLORS: Record<string, string> = {
  cast: 'var(--active-glow)',
  resolve: 'var(--life-high)',
  damage: 'var(--life-low)',
  life_change: 'var(--life-mid)',
  attack: 'var(--mtg-red)',
  block: 'var(--mtg-white)',
  game_end: 'var(--life-high)',
  zone_change: 'var(--text-secondary)',
  trigger: '#c9a0ff',
  activate: 'var(--mtg-blue)',
  draw: 'var(--text-muted)',
}

export function ActionLog({ gameId }: ActionLogProps) {
  const { entries } = useTranscript(gameId)
  const scrollRef = useRef<HTMLDivElement>(null)

  const filtered = entries.filter(e => VISIBLE_EVENTS.has(e.event_type))

  // Group entries by turn number
  const byTurn: { turn: number; entries: typeof filtered }[] = []
  for (const entry of filtered) {
    const last = byTurn[byTurn.length - 1]
    if (last && last.turn === entry.turn) {
      last.entries.push(entry)
    } else {
      byTurn.push({ turn: entry.turn, entries: [entry] })
    }
  }

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [filtered.length])

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: 'var(--bg-secondary)',
      borderRadius: '8px',
      border: '1px solid var(--border-default)',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '0.5rem 0.75rem',
        borderBottom: '1px solid var(--border-muted)',
        fontWeight: 700,
        fontSize: '0.85rem',
      }}>
        Action Log
      </div>
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '0.5rem',
        }}
      >
        {filtered.length === 0 && (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center', padding: '1rem' }}>
            Waiting for game actions...
          </div>
        )}
        {byTurn.map(({ turn, entries: turnEntries }) => (
          <div key={turn}>
            <div style={{
              fontSize: '0.65rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--text-muted)',
              padding: '0.4rem 0.25rem 0.2rem',
              borderBottom: '1px solid var(--border-muted)',
              marginBottom: '0.25rem',
            }}>
              Turn {turn}
            </div>
            {turnEntries.map((entry) => (
              <div
                key={entry.seq}
                style={{
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.75rem',
                  lineHeight: 1.4,
                  borderLeft: `2px solid ${EVENT_COLORS[entry.event_type] || 'var(--border-muted)'}`,
                  marginBottom: '0.25rem',
                  color: 'var(--text-primary)',
                }}
              >
                {entry.description}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
