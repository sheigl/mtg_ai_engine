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
  cast: 'var(--accent)',
  resolve: 'var(--success)',
  damage: 'var(--danger)',
  life_change: 'var(--warning)',
  attack: 'var(--mtg-red)',
  block: 'var(--mtg-white)',
  game_end: 'var(--success)',
  zone_change: 'var(--text-secondary)',
  trigger: '#c9a0ff',
  activate: 'var(--mtg-blue)',
  draw: 'var(--text-muted)',
}

export function ActionLog({ gameId }: ActionLogProps) {
  const { entries } = useTranscript(gameId)
  const scrollRef = useRef<HTMLDivElement>(null)

  const filtered = entries.filter(e => VISIBLE_EVENTS.has(e.event_type))

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
      background: 'var(--surface-elevated)',
      borderRadius: 'var(--radius-lg)',
      border: '1px solid var(--border-subtle)',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: 'var(--space-3) var(--space-4)',
        borderBottom: '1px solid var(--border-subtle)',
        fontWeight: 700,
        fontSize: 'var(--text-sm)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-2)',
      }}>
        <span style={{ fontSize: 'var(--text-xs)' }}>📜</span>
        Action Log
      </div>
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 'var(--space-2)',
        }}
      >
        {filtered.length === 0 && (
          <div style={{
            color: 'var(--text-muted)',
            fontSize: 'var(--text-sm)',
            textAlign: 'center',
            padding: 'var(--space-8) var(--space-4)',
          }}>
            Waiting for game actions...
          </div>
        )}
        {byTurn.map(({ turn, entries: turnEntries }) => (
          <div key={turn}>
            <div style={{
              fontSize: 'var(--text-xs)',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--text-muted)',
              padding: 'var(--space-2) var(--space-2) var(--space-1)',
              borderBottom: '1px solid var(--border-subtle)',
              marginBottom: 'var(--space-1)',
            }}>
              Turn {turn}
            </div>
            {turnEntries.map((entry) => (
              <div
                key={entry.seq}
                style={{
                  padding: 'var(--space-1) var(--space-2)',
                  fontSize: 'var(--text-xs)',
                  lineHeight: 'var(--leading-normal)',
                  borderLeft: `2px solid ${EVENT_COLORS[entry.event_type] || 'var(--border-subtle)'}`,
                  marginBottom: 'var(--space-1)',
                  color: 'var(--text-primary)',
                  borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
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
