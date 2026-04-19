import { useNavigate } from 'react-router-dom'

interface GameResultOverlayProps {
  isGameOver: boolean
  winner: string | null
  humanPlayerName: string
  gameId: string
}

export function GameResultOverlay({ isGameOver, winner, humanPlayerName, gameId }: GameResultOverlayProps) {
  const navigate = useNavigate()

  if (!isGameOver) return null

  const isDraw = winner === 'draw' || winner === null
  const isWin = !isDraw && winner === humanPlayerName

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,0.8)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 300,
    }}>
      <div style={{
        background: 'var(--bg-secondary)',
        border: `2px solid ${isDraw ? 'var(--border-default)' : isWin ? '#4a9a64' : '#e55'}`,
        borderRadius: '12px',
        padding: '2rem 3rem',
        textAlign: 'center',
        boxShadow: '0 12px 48px rgba(0,0,0,0.6)',
        minWidth: '280px',
      }}>
        <div style={{
          fontSize: '3rem',
          marginBottom: '0.5rem',
        }}>
          {isDraw ? '🤝' : isWin ? '🏆' : '💀'}
        </div>
        <div style={{
          fontSize: '2rem',
          fontWeight: 900,
          color: isDraw ? 'var(--text-primary)' : isWin ? '#4a9a64' : '#e55',
          marginBottom: '0.5rem',
        }}>
          {isDraw ? 'Draw' : isWin ? 'Victory!' : 'Defeat'}
        </div>
        {!isDraw && (
          <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            {isWin ? 'You won the game!' : `${winner} wins`}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <button
            onClick={() => navigate('/human-game/create')}
            style={{
              background: 'var(--active-glow)',
              color: '#000',
              border: 'none',
              borderRadius: '6px',
              padding: '0.6rem 1.5rem',
              fontWeight: 700,
              cursor: 'pointer',
              fontSize: '0.9rem',
            }}
          >
            Play Again
          </button>
          <button
            onClick={() => navigate(`/game/${gameId}`)}
            style={{
              background: 'var(--bg-tertiary)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-muted)',
              borderRadius: '6px',
              padding: '0.5rem 1.5rem',
              cursor: 'pointer',
              fontSize: '0.85rem',
            }}
          >
            Watch Replay
          </button>
          <button
            onClick={() => navigate('/')}
            style={{
              background: 'none',
              color: 'var(--text-muted)',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.8rem',
              padding: '0.25rem',
            }}
          >
            ← Back to Games
          </button>
        </div>
      </div>
    </div>
  )
}
