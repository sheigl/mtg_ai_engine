import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useGameState } from '../hooks/useGameState'
import { PlayerZone } from './PlayerZone'
import { Battlefield } from './Battlefield'
import { StackView } from './StackView'
import { PhaseTracker } from './PhaseTracker'
import { ConnectionStatus } from './ConnectionStatus'
import { GameSidebar } from './GameSidebar'
import type { GameState } from '../types/game'
import '../styles/board.css'

function getPlayerPermanents(gs: GameState, playerName: string) {
  return gs.battlefield.filter(p => p.controller === playerName)
}

function GameOverOverlay({
  gs,
  gameId,
  onDismiss,
}: {
  gs: GameState
  gameId: string
  onDismiss: () => void
}) {
  const navigate = useNavigate()
  if (!gs.is_game_over) return null

  function downloadLog() {
    const a = document.createElement('a')
    a.href = `/export/${gameId}/game-log`
    a.download = `game-log-${gameId}.txt`
    a.click()
  }

  return (
    <div className="modal-backdrop">
      <div className="modal-panel" style={{ textAlign: 'center', maxWidth: 400 }}>
        <div style={{
          fontSize: 'var(--text-3xl)',
          fontWeight: 800,
          marginBottom: 'var(--space-3)',
          color: 'var(--text-primary)',
        }}>
          Game Over
        </div>
        <div style={{
          fontSize: 'var(--text-xl)',
          fontWeight: 600,
          color: gs.winner === 'draw' ? 'var(--warning)' : 'var(--success)',
          marginBottom: 'var(--space-6)',
        }}>
          {gs.winner === 'draw' ? 'Draw!' : `${gs.winner} wins!`}
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: 'center', flexWrap: 'wrap' }}>
          <button className="btn btn--secondary" onClick={onDismiss}>View Board</button>
          <button className="btn btn--secondary" onClick={downloadLog}>↓ Download Log</button>
          <button className="btn btn--primary" onClick={() => navigate('/')}>← Back to Games</button>
        </div>
      </div>
    </div>
  )
}

export function GameBoard() {
  const { gameId } = useParams<{ gameId: string }>()
  const { data: gs, isLoading, isError, error } = useGameState(gameId)
  const navigate = useNavigate()
  const [gameOverDismissed, setGameOverDismissed] = useState(false)

  if (isError) {
    const isNotFound = error instanceof Error && error.message === 'GAME_NOT_FOUND'
    return (
      <div className="center-message">
        <ConnectionStatus isError={!isNotFound} isLoading={false} />
        <div style={{ color: 'var(--danger)', fontSize: 'var(--text-lg)', fontWeight: 600, marginBottom: 'var(--space-4)' }}>
          {isNotFound ? 'Game has ended or was not found.' : 'Connection lost. Retrying...'}
        </div>
        <button className="btn btn--primary" onClick={() => navigate('/')}>Back to Games</button>
      </div>
    )
  }

  if (isLoading || !gs) {
    return (
      <div className="center-message">
        <div className="spinner" style={{ marginBottom: 'var(--space-4)' }} />
        <span style={{ color: 'var(--text-secondary)' }}>Loading game...</span>
      </div>
    )
  }

  const player1 = gs.players[0]
  const player2 = gs.players[1]
  const p1Permanents = getPlayerPermanents(gs, player1.name)
  const p2Permanents = getPlayerPermanents(gs, player2.name)
  const isCommander = gs.format === 'commander'

  function downloadGameLog() {
    const a = document.createElement('a')
    a.href = `/export/${gameId}/game-log`
    a.download = `game-log-${gameId}.txt`
    a.click()
  }

  return (
    <div className="game-board with-sidebar">
      <div className="board-actions">
        <button className="btn btn--secondary btn--sm" onClick={() => navigate('/')}>← Games</button>
        <button className="btn btn--ghost btn--sm" onClick={downloadGameLog} title="Download turn-by-turn game log">↓ Log</button>
      </div>

      {/* Opponent (Player 2) info */}
      <PlayerZone
        player={player2}
        isActive={gs.active_player === player2.name}
        isOpponent
        format={gs.format}
        commanderDamage={isCommander ? gs.commander_damage[player2.name] : undefined}
      />

      {/* Opponent battlefield */}
      <Battlefield permanents={p2Permanents} isOpponent />

      {/* Center bar: Stack + Phase */}
      <div className="center-bar">
        <StackView stack={gs.stack} />
        <PhaseTracker
          turn={gs.turn}
          phase={gs.phase}
          step={gs.step}
          activePlayer={gs.active_player}
        />
      </div>

      {/* Player 1 battlefield */}
      <Battlefield permanents={p1Permanents} />

      {/* Player 1 info */}
      <PlayerZone
        player={player1}
        isActive={gs.active_player === player1.name}
        format={gs.format}
        commanderDamage={isCommander ? gs.commander_damage[player1.name] : undefined}
      />

      {/* Sidebar with Action Log / AI tabs */}
      <div className="action-log-container">
        <GameSidebar gameId={gs.game_id} isGameOver={gs.is_game_over} />
      </div>

      {/* Game over overlay */}
      {!gameOverDismissed && (
        <GameOverOverlay gs={gs} gameId={gs.game_id} onDismiss={() => setGameOverDismissed(true)} />
      )}
    </div>
  )
}
