import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useGameState } from '../hooks/useGameState'
import { PlayerZone } from './PlayerZone'
import { Battlefield } from './Battlefield'
import { StackView } from './StackView'
import { PhaseTracker } from './PhaseTracker'
import { ConnectionStatus } from './ConnectionStatus'
import { ActionLog } from './ActionLog'
import { DebugPanel } from './DebugPanel'
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
    <div className="game-over-overlay">
      <div className="game-over-box">
        <div className="game-over-title">Game Over</div>
        <div className="game-over-winner">
          {gs.winner === 'draw' ? 'Draw!' : `${gs.winner} wins!`}
        </div>
        <div className="game-over-actions">
          <button onClick={onDismiss}>View Board</button>
          <button onClick={downloadLog}>↓ Download Log</button>
          <button onClick={() => navigate('/')}>← Back to Games</button>
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
      <div className="error-container">
        <ConnectionStatus isError={!isNotFound} isLoading={false} />
        <div className="error-message">
          {isNotFound ? 'Game has ended or was not found.' : 'Connection lost. Retrying...'}
        </div>
        <button onClick={() => navigate('/')}>Back to Games</button>
      </div>
    )
  }

  if (isLoading || !gs) {
    return (
      <div className="loading-container">
        <ConnectionStatus isError={false} isLoading={true} />
        Loading game...
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
      <ConnectionStatus isError={false} isLoading={false} />

      <div className="top-left-buttons">
        <button onClick={() => navigate('/')}>← Games</button>
        <button onClick={downloadGameLog} title="Download turn-by-turn game log">↓ Download Log</button>
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

      {/* Action Log sidebar */}
      <div className="action-log-container">
        <ActionLog gameId={gs.game_id} />
      </div>

      {/* Game over overlay */}
      {!gameOverDismissed && (
        <GameOverOverlay gs={gs} gameId={gs.game_id} onDismiss={() => setGameOverDismissed(true)} />
      )}

      {/* Debug Panel */}
      <DebugPanel gameId={gs.game_id} isGameOver={gs.is_game_over} debugEnabled={gs.debug_enabled} />
    </div>
  )
}
