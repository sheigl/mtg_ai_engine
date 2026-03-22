import { Link } from 'react-router-dom'
import { useGameList } from '../hooks/useGameList'
import { ConnectionStatus } from './ConnectionStatus'
import '../styles/board.css'

const PHASE_LABELS: Record<string, string> = {
  beginning: 'Beginning',
  precombat_main: 'Main 1',
  combat: 'Combat',
  postcombat_main: 'Main 2',
  ending: 'End',
}

export function GameList() {
  const { data: games, isLoading, isError } = useGameList()

  return (
    <div style={{
      maxWidth: 800,
      margin: '0 auto',
      padding: '2rem 1rem',
    }}>
      <ConnectionStatus isError={isError} isLoading={isLoading && !games} />

      <h1 style={{ marginBottom: '0.5rem' }}>MTG Game Observer</h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
        Watch AI vs AI games in real time
      </p>

      {isLoading && !games && (
        <div style={{ color: 'var(--text-muted)', padding: '2rem', textAlign: 'center' }}>
          Loading games...
        </div>
      )}

      {games && games.length === 0 && (
        <div style={{
          padding: '3rem',
          textAlign: 'center',
          color: 'var(--text-muted)',
          background: 'var(--bg-secondary)',
          borderRadius: '8px',
          border: '1px solid var(--border-default)',
        }}>
          <div style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>No active games</div>
          <div style={{ fontSize: '0.85rem' }}>Start a game via the API to begin observing</div>
        </div>
      )}

      {games && games.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {games.map(game => (
            <Link
              key={game.game_id}
              to={`/game/${game.game_id}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '1rem 1.25rem',
                background: game.is_game_over ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                borderRadius: '8px',
                border: `1px solid ${game.is_game_over ? 'var(--border-muted)' : 'var(--border-default)'}`,
                textDecoration: 'none',
                color: 'inherit',
                opacity: game.is_game_over ? 0.6 : 1,
                transition: 'border-color var(--transition-fast)',
              }}
              onMouseEnter={e => {
                if (!game.is_game_over) {
                  (e.currentTarget as HTMLElement).style.borderColor = 'var(--active-glow)'
                }
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.borderColor = game.is_game_over ? 'var(--border-muted)' : 'var(--border-default)'
              }}
            >
              <div>
                <div style={{ fontWeight: 700, fontSize: '1rem' }}>
                  {game.player1_name} vs {game.player2_name}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                  {game.is_game_over
                    ? `Finished — ${game.winner === 'draw' ? 'Draw' : `${game.winner} wins`}`
                    : `Turn ${game.turn} — ${PHASE_LABELS[game.phase] || game.phase}`
                  }
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{
                  padding: '0.2rem 0.6rem',
                  borderRadius: '4px',
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  background: game.format === 'commander' ? '#4a2d6e' : 'var(--bg-tertiary)',
                  color: game.format === 'commander' ? '#c9a0ff' : 'var(--text-secondary)',
                }}>
                  {game.format}
                </span>
                {!game.is_game_over && (
                  <span style={{ color: 'var(--active-glow)', fontSize: '0.85rem' }}>→</span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
