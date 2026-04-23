import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useGameList } from '../hooks/useGameList'
import { useQueryClient } from '@tanstack/react-query'

const COLOR_CSS: Record<string, string> = {
  W: '#f9fafb', U: '#3b82f6', B: '#1e1e1e', R: '#ef4444', G: '#22c55e',
}

function ColorPips({ colors }: { colors: string[] | undefined }) {
  if (!colors || colors.length === 0) return null
  return (
    <span style={{ display: 'inline-flex', gap: 1, marginLeft: 4 }}>
      {colors.map(c => (
        <span
          key={c}
          style={{
            fontSize: 10,
            fontWeight: 700,
            color: COLOR_CSS[c] ?? 'var(--text-tertiary)',
            background: c === 'B' ? 'var(--text-secondary, #666)' : 'transparent',
            borderRadius: 2,
            padding: '0 1px',
            lineHeight: 1,
          }}
        >
          {c}
        </span>
      ))}
    </span>
  )
}

const PHASE_LABELS: Record<string, string> = {
  beginning: 'Beginning',
  precombat_main: 'Main 1',
  combat: 'Combat',
  postcombat_main: 'Main 2',
  ending: 'End',
}

function GameStatusBadge({ isGameOver, winner, activePlayer }: { isGameOver: boolean; winner: string; activePlayer?: string }) {
  if (isGameOver) {
    return winner === 'draw'
      ? <span className="badge badge--warning">Draw</span>
      : <span className="badge badge--success">{winner} wins</span>
  }
  return <span className="badge badge--accent">{activePlayer}'s turn</span>
}

function FormatBadge({ format }: { format: string }) {
  if (format === 'commander') {
    return <span className="badge badge--muted" style={{ background: 'linear-gradient(135deg, var(--mtg-white), var(--mtg-blue), var(--mtg-black), var(--mtg-red), var(--mtg-green))', color: '#fff', border: 'none' }}>Commander</span>
  }
  return <span className="badge badge--muted">Standard</span>
}

export function GameList() {
  const { data: games, isLoading } = useGameList()
  const [showCreateForm, setShowCreateForm] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const deleteGame = async (gameId: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    await fetch(`/game/${gameId}`, { method: 'DELETE' })
    queryClient.invalidateQueries({ queryKey: ['gameList'] })
  }

  const activeGames = games?.filter(g => !g.is_game_over) ?? []
  const completedGames = games?.filter(g => g.is_game_over) ?? []

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: 'var(--space-6) var(--space-4)' }}>
      {/* Hero */}
      <div style={{
        textAlign: 'center',
        marginBottom: 'var(--space-8)',
        padding: 'var(--space-8) var(--space-4)',
        background: 'linear-gradient(135deg, var(--surface-elevated) 0%, var(--surface-hover) 100%)',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--border-subtle)',
      }}>
        <div style={{
          width: 64,
          height: 64,
          margin: '0 auto var(--space-4)',
          borderRadius: 'var(--radius-xl)',
          background: 'linear-gradient(135deg, var(--mtg-blue), var(--mtg-black))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '2rem',
          boxShadow: 'var(--shadow-lg)',
        }}>
          <span style={{ filter: 'grayscale(1) brightness(2)' }}>♠</span>
        </div>
        <h1 style={{
          fontSize: 'var(--text-3xl)',
          fontWeight: 800,
          marginBottom: 'var(--space-2)',
          letterSpacing: '-0.02em',
          background: 'linear-gradient(135deg, var(--text-primary), var(--accent))',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          MTG Game Engine
        </h1>
        <p style={{
          color: 'var(--text-secondary)',
          fontSize: 'var(--text-base)',
          maxWidth: 480,
          margin: '0 auto var(--space-6)',
          lineHeight: 'var(--leading-relaxed)',
        }}>
          Watch AI vs AI games or play against a bot in real time.
          Full rules engine with Commander support.
        </p>
        <div style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: 'center', flexWrap: 'wrap' }}>
          <button
            className="btn btn--success btn--lg"
            onClick={() => navigate('/human-game/create')}
          >
            <span>▶</span> Play vs AI
          </button>
          <button
            className="btn btn--primary btn--lg"
            onClick={() => setShowCreateForm(true)}
          >
            <span>+</span> New AI Game
          </button>
        </div>
      </div>

      {/* Create game modal */}
      {showCreateForm && (
        <div
          className="modal-backdrop"
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 400,
            background: 'rgba(0, 0, 0, 0.6)',
            backdropFilter: 'blur(4px)',
            WebkitBackdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 'var(--space-4)',
            animation: 'fade-in 200ms ease',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              animation: 'slide-up 300ms ease',
              maxHeight: '90vh',
              overflow: 'auto',
            }}
          >
            {/* Import CreateGameForm inline to avoid lazy load issues */}
            <CreateGameFormLazy onClose={() => setShowCreateForm(false)} />
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && !games && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 'var(--space-3)',
          padding: 'var(--space-12)',
          color: 'var(--text-tertiary)',
        }}>
          <div className="spinner" />
          <span style={{ fontSize: 'var(--text-sm)' }}>Loading games...</span>
        </div>
      )}

      {/* Empty state */}
      {games && games.length === 0 && (
        <div style={{
          textAlign: 'center',
          padding: 'var(--space-12) var(--space-4)',
          background: 'var(--surface-elevated)',
          borderRadius: 'var(--radius-xl)',
          border: '1px solid var(--border-subtle)',
        }}>
          <div style={{
            fontSize: '3rem',
            marginBottom: 'var(--space-4)',
            opacity: 0.3,
          }}>
            ♠
          </div>
          <h3 style={{
            fontSize: 'var(--text-xl)',
            fontWeight: 600,
            marginBottom: 'var(--space-2)',
            color: 'var(--text-primary)',
          }}>
            No games yet
          </h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-6)' }}>
            Start your first game to see it here.
          </p>
          <div style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: 'center' }}>
            <button className="btn btn--success" onClick={() => navigate('/human-game/create')}>
              <span>▶</span> Play vs AI
            </button>
            <button className="btn btn--primary" onClick={() => setShowCreateForm(true)}>
              <span>+</span> New AI Game
            </button>
          </div>
        </div>
      )}

      {/* Active Games */}
      {activeGames.length > 0 && (
        <section style={{ marginBottom: 'var(--space-8)' }}>
          <h2 style={{
            fontSize: 'var(--text-sm)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--text-tertiary)',
            marginBottom: 'var(--space-4)',
          }}>
            Active Games
          </h2>
          <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
            {activeGames.map(game => (
              <GameCard key={game.game_id} game={game} onDelete={deleteGame} />
            ))}
          </div>
        </section>
      )}

      {/* Completed Games */}
      {completedGames.length > 0 && (
        <section>
          <h2 style={{
            fontSize: 'var(--text-sm)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--text-tertiary)',
            marginBottom: 'var(--space-4)',
          }}>
            Completed
          </h2>
          <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
            {completedGames.map(game => (
              <GameCard key={game.game_id} game={game} onDelete={deleteGame} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function GameCard({ game, onDelete }: { game: any; onDelete: (id: string, e: React.MouseEvent) => void }) {
  const isOver = game.is_game_over

  return (
    <Link
      to={isOver ? `/game/${game.game_id}` : `/game/${game.game_id}`}
      className="card-surface"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-4)',
        padding: 'var(--space-4)',
        textDecoration: 'none',
        color: 'inherit',
        opacity: isOver ? 0.7 : 1,
        borderLeft: isOver ? '3px solid transparent' : '3px solid var(--accent)',
        transition: 'all var(--transition-fast)',
      }}
      onMouseEnter={e => {
        if (!isOver) {
          e.currentTarget.style.borderLeftColor = 'var(--accent-hover)'
          e.currentTarget.style.boxShadow = 'var(--shadow-md)'
        }
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderLeftColor = isOver ? 'transparent' : 'var(--accent)'
        e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
      }}
    >
      {/* Player avatars */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexShrink: 0 }}>
        <PlayerAvatar name={game.player1_name} color="var(--mtg-blue)" />
        <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)', fontWeight: 600 }}>VS</span>
        <PlayerAvatar name={game.player2_name} color="var(--mtg-red)" />
      </div>

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontWeight: 700,
          fontSize: 'var(--text-base)',
          marginBottom: 'var(--space-1)',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>
          {game.player1_name} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>vs</span> {game.player2_name}
        </div>
        {(game.player1_deck_name || game.player2_deck_name || (game.player1_color_identity?.length) || (game.player2_color_identity?.length)) && (
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginBottom: 'var(--space-1)', display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
            <span>
              <span style={{ fontWeight: 600 }}>{game.player1_name}</span>
              {game.player1_deck_name && <span style={{ color: 'var(--text-tertiary)' }}> {game.player1_deck_name}</span>}
              <ColorPips colors={game.player1_color_identity} />
            </span>
            <span style={{ color: 'var(--text-muted)' }}>vs</span>
            <span>
              <span style={{ fontWeight: 600 }}>{game.player2_name}</span>
              {game.player2_deck_name && <span style={{ color: 'var(--text-tertiary)' }}> {game.player2_deck_name}</span>}
              <ColorPips colors={game.player2_color_identity} />
            </span>
          </div>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
          <GameStatusBadge
            isGameOver={game.is_game_over}
            winner={game.winner}
            activePlayer={game.active_player}
          />
          <FormatBadge format={game.format} />
          {game.series_id && game.series_total && game.series_total > 1 && (
            <span className="badge badge--muted">
              {game.series_game_number ?? 1} / {game.series_total}
            </span>
          )}
          {game.series_id && game.series_score && Object.keys(game.series_score).length > 0 && (
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', fontWeight: 600 }}>
              {Object.entries(game.series_score).map(([name, wins], i) => (
                <span key={name}>
                  {i > 0 && ' — '}
                  {name}: {wins as number}
                </span>
              ))}
            </span>
          )}
          {!game.is_game_over && (
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)' }}>
              Turn {game.turn} · {PHASE_LABELS[game.phase] || game.phase}
            </span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexShrink: 0 }}>
        {!game.is_game_over && (
          <span style={{ color: 'var(--accent)', fontSize: 'var(--text-sm)' }}>→</span>
        )}
        <button
          onClick={e => onDelete(game.game_id, e)}
          title="Delete game"
          className="btn btn--ghost btn--sm btn--icon"
          style={{ width: 32, height: 32, color: 'var(--text-muted)' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--danger)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
        >
          ✕
        </button>
      </div>
    </Link>
  )
}

function PlayerAvatar({ name, color }: { name: string; color: string }) {
  const initial = name.charAt(0).toUpperCase()
  return (
    <div style={{
      width: 36,
      height: 36,
      borderRadius: '50%',
      background: color,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: 'var(--text-sm)',
      fontWeight: 700,
      color: '#fff',
      flexShrink: 0,
      boxShadow: 'var(--shadow-sm)',
    }}>
      {initial}
    </div>
  )
}

// Lazy wrapper to avoid circular import issues
import { CreateGameForm } from './CreateGameForm'
function CreateGameFormLazy({ onClose }: { onClose: () => void }) {
  return <CreateGameForm onClose={onClose} />
}
