import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { useGameState } from '../hooks/useGameState'
import { useLegalActions, type LegalAction } from '../hooks/useLegalActions'
import { useHumanAction } from '../hooks/useHumanAction'
import { PlayerZone } from './PlayerZone'
import { Battlefield } from './Battlefield'
import { StackView } from './StackView'
import { PhaseTracker } from './PhaseTracker'
import { ConnectionStatus } from './ConnectionStatus'
import { ActionLog } from './ActionLog'
import { InteractiveHand } from './InteractiveHand'
import { ActionPanel } from './ActionPanel'
import { BlockerAssigner } from './BlockerAssigner'
import { TargetChoiceModal, MulliganModal, DiscardModal } from './ChoiceModal'
import { GameResultOverlay } from './GameResultOverlay'
import type { GameState, Permanent } from '../types/game'
import '../styles/board.css'

function getPlayerPermanents(gs: GameState, playerName: string) {
  return gs.battlefield.filter(p => p.controller === playerName)
}

function getCreatures(permanents: Permanent[]) {
  return permanents.filter(p => p.card.type_line.includes('Creature'))
}

function getAttackingCreatures(gs: GameState): Permanent[] {
  if (!gs.combat) return []
  return gs.combat.attackers
    .map(a => gs.battlefield.find(p => p.id === a.permanent_id))
    .filter((p): p is Permanent => !!p)
}

export function HumanGameBoard() {
  const { gameId } = useParams<{ gameId: string }>()
  const location = useLocation()
  const navigate = useNavigate()

  // Persist humanPlayerName across refreshes — fall back to server lookup
  const [humanPlayerName, setHumanPlayerName] = useState<string>(() => {
    const fromNav = (location.state as { humanPlayerName?: string } | null)?.humanPlayerName
    if (fromNav) {
      localStorage.setItem(`hgb-player-${gameId}`, fromNav)
      return fromNav
    }
    return localStorage.getItem(`hgb-player-${gameId}`) ?? ''
  })

  // If name is unknown, fetch it from the server
  useEffect(() => {
    if (humanPlayerName || !gameId) return
    fetch(`/human-game/${gameId}/player`)
      .then(r => r.ok ? r.json() : null)
      .then(json => {
        const name: string = json?.data?.human_player_name
        if (name) {
          localStorage.setItem(`hgb-player-${gameId}`, name)
          setHumanPlayerName(name)
        }
      })
      .catch(() => {})
  }, [gameId, humanPlayerName])

  const { data: gs, isLoading, isError, error } = useGameState(gameId)
  const { isMyTurn, legalActions, legalActionsByCard, step, phase } = useLegalActions(gameId, humanPlayerName)
  const { submitAction, isPending, lastError, clearError } = useHumanAction(gameId)

  // ── Interactive state ────────────────────────────────────────────────────────
  const [selectedAttackers, setSelectedAttackers] = useState<Set<string>>(new Set())
  const [blockerAssignments, setBlockerAssignments] = useState<Map<string, string>>(new Map())
  const [pendingCast, setPendingCast] = useState<{ action: LegalAction; cardId: string } | null>(null)
  const [autoPassPriority, setAutoPassPriority] = useState(() =>
    localStorage.getItem('hgb-auto-pass') === 'true',
  )
  const [_gameOverDismissed] = useState(false)
  const [draggedCardId, setDraggedCardId] = useState<string | null>(null)

  // Reset combat state when step changes
  useEffect(() => {
    if (step !== 'declare_attackers') setSelectedAttackers(new Set())
    if (step !== 'declare_blockers') setBlockerAssignments(new Map())
  }, [step])

  // Auto-pass priority when enabled and only "pass" is available
  useEffect(() => {
    if (!isMyTurn || !autoPassPriority || isPending) return
    if (legalActions.length === 1 && legalActions[0].action_type === 'pass') {
      const timer = setTimeout(() => submitAction('pass', {}), 300)
      return () => clearTimeout(timer)
    }
  }, [isMyTurn, autoPassPriority, isPending, legalActions, submitAction])

  // ── Action handlers ──────────────────────────────────────────────────────────

  const handlePlayLand = useCallback((cardId: string) => {
    submitAction('play_land', { card_id: cardId })
  }, [submitAction])

  const handleCastSpell = useCallback((action: LegalAction, cardId: string) => {
    const targets = action.valid_targets ?? []
    const needsX = action.x_value !== undefined && action.x_value !== null
    if (targets.length > 0 || needsX) {
      setPendingCast({ action, cardId })
    } else {
      submitAction('cast', {
        card_id: cardId,
        targets: [],
        mana_payment: {},
        x_value: null,
        face_index: action.face_index ?? 0,
      })
    }
  }, [submitAction])

  const handleCastConfirm = useCallback((target: string, xValue?: number) => {
    if (!pendingCast) return
    submitAction('cast', {
      card_id: pendingCast.cardId,
      targets: target ? [target] : [],
      mana_payment: {},
      x_value: xValue ?? null,
      face_index: pendingCast.action.face_index ?? 0,
      ...(pendingCast.action.alternative_cost ? { alternative_cost: pendingCast.action.alternative_cost } : {}),
      ...(pendingCast.action.from_graveyard ? { from_graveyard: true } : {}),
    })
    setPendingCast(null)
  }, [pendingCast, submitAction])

  const handleToggleAttacker = useCallback((permanentId: string) => {
    setSelectedAttackers(prev => {
      const next = new Set(prev)
      if (next.has(permanentId)) next.delete(permanentId)
      else next.add(permanentId)
      return next
    })
  }, [])

  const handleConfirmAttackers = useCallback(() => {
    submitAction('declare_attackers', { attacker_ids: [...selectedAttackers] })
  }, [submitAction, selectedAttackers])

  const handleAssignBlocker = useCallback((blockerId: string, attackerId: string) => {
    setBlockerAssignments(prev => new Map(prev).set(blockerId, attackerId))
  }, [])

  const handleUnassignBlocker = useCallback((blockerId: string) => {
    setBlockerAssignments(prev => {
      const next = new Map(prev)
      next.delete(blockerId)
      return next
    })
  }, [])

  const handleConfirmBlockers = useCallback(() => {
    const assignments = [...blockerAssignments.entries()].map(([blocker_id, attacker_id]) => ({
      blocker_id,
      attacker_id,
    }))
    submitAction('declare_blockers', { assignments })
  }, [submitAction, blockerAssignments])

  const handlePassPriority = useCallback(() => {
    submitAction('pass', {})
  }, [submitAction])

  const handleToggleAutoPass = useCallback(() => {
    setAutoPassPriority(prev => {
      const next = !prev
      localStorage.setItem('hgb-auto-pass', String(next))
      return next
    })
  }, [])

  // ── Mulligan detection ───────────────────────────────────────────────────────
  // Backend uses action_type="declare_mulligan"; "Keep hand" description = keep, otherwise = mulligan
  const mulliganActions = legalActions.filter(a => a.action_type === 'declare_mulligan')
  const isMulliganPhase = mulliganActions.length > 0
  const keepAction = mulliganActions.find(a => a.description?.toLowerCase().includes('keep'))
  const doMulliganAction = mulliganActions.find(a => !a.description?.toLowerCase().includes('keep'))

  // ── Discard detection ────────────────────────────────────────────────────────
  const discardActions = legalActions.filter(a => a.action_type === 'discard')
  const isDiscardPhase = discardActions.length > 0 && legalActions.every(a => a.action_type === 'discard')

  // ── Error / loading states ───────────────────────────────────────────────────
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

  if (isLoading || !gs || !humanPlayerName) {
    return (
      <div className="loading-container">
        <ConnectionStatus isError={false} isLoading={true} />
        Loading game...
      </div>
    )
  }

  const humanPlayer = gs.players.find(p => p.name === humanPlayerName) ?? gs.players[0]
  const opponentPlayer = gs.players.find(p => p.name !== humanPlayerName) ?? gs.players[1]
  const humanPermanents = getPlayerPermanents(gs, humanPlayer.name)
  const opponentPermanents = getPlayerPermanents(gs, opponentPlayer.name)
  const isCommander = gs.format === 'commander'

  // Legal blocker IDs — any creature the human controls that's not tapped
  const legalBlockerIds = new Set(
    getCreatures(humanPermanents)
      .filter(p => !p.tapped)
      .map(p => p.id),
  )

  const attackingCreatures = getAttackingCreatures(gs)
  const isResponseWindow = isMyTurn && gs.active_player !== humanPlayer.name

  return (
    <div className="game-board with-sidebar">
      <ConnectionStatus isError={false} isLoading={false} />

      <div className="top-left-buttons">
        <button onClick={() => navigate('/')}>← Games</button>
        <button onClick={() => navigate(`/game/${gs.game_id}`)} title="Open AI observer view">
          Observer View
        </button>
      </div>

      {/* Opponent zone */}
      <PlayerZone
        player={opponentPlayer}
        isActive={gs.active_player === opponentPlayer.name}
        isOpponent
        format={gs.format}
        commanderDamage={isCommander ? gs.commander_damage[opponentPlayer.name] : undefined}
      />

      {/* Opponent battlefield */}
      <Battlefield permanents={opponentPermanents} isOpponent />

      {/* Center */}
      <div className="center-bar">
        <StackView stack={gs.stack} />
        <PhaseTracker
          turn={gs.turn}
          phase={gs.phase}
          step={gs.step}
          activePlayer={gs.active_player}
        />
      </div>

      {/* Human battlefield with attacker/blocker overlays */}
      <div
        style={{ position: 'relative' }}
        onDragOver={draggedCardId ? (e) => e.preventDefault() : undefined}
        onDrop={draggedCardId ? (e) => {
          e.preventDefault()
          const actions = legalActionsByCard.get(draggedCardId)
          const playLandAction = actions?.find(a => a.action_type === 'play_land')
          const castAction = actions?.find(a => a.action_type === 'cast')
          if (playLandAction) handlePlayLand(draggedCardId)
          else if (castAction) handleCastSpell(castAction, draggedCardId)
          setDraggedCardId(null)
        } : undefined}
      >
        <Battlefield permanents={humanPermanents} />
        {isMyTurn && step === 'declare_attackers' && (
          <div style={{ marginTop: '0.5rem' }}>
            <div style={{ fontSize: '0.75rem', color: '#e55', fontWeight: 600, marginBottom: '0.25rem' }}>
              Click creatures to attack:
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
              {getCreatures(humanPermanents)
                .filter(p => !p.tapped && !p.summoning_sick)
                .map(creature => (
                  <button
                    key={creature.id}
                    onClick={() => handleToggleAttacker(creature.id)}
                    disabled={isPending}
                    style={{
                      background: selectedAttackers.has(creature.id) ? '#e55' : 'var(--bg-secondary)',
                      color: selectedAttackers.has(creature.id) ? '#fff' : 'var(--text-secondary)',
                      border: `1px solid ${selectedAttackers.has(creature.id) ? '#e55' : 'var(--border-default)'}`,
                      borderRadius: '4px',
                      padding: '0.25rem 0.5rem',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                    }}
                  >
                    {creature.card.name} ({creature.card.power}/{creature.card.toughness})
                  </button>
                ))}
            </div>
          </div>
        )}
        {isMyTurn && step === 'declare_blockers' && attackingCreatures.length > 0 && (
          <BlockerAssigner
            myCreatures={getCreatures(humanPermanents)}
            attackingCreatures={attackingCreatures}
            assignments={blockerAssignments}
            legalBlockerIds={legalBlockerIds}
            isPending={isPending}
            onAssign={handleAssignBlocker}
            onUnassign={handleUnassignBlocker}
          />
        )}
      </div>

      {/* Human hand — interactive when it's the human's turn */}
      <div>
        <PlayerZone
          player={humanPlayer}
          isActive={gs.active_player === humanPlayer.name}
          format={gs.format}
          commanderDamage={isCommander ? gs.commander_damage[humanPlayer.name] : undefined}
        />
        {isMyTurn ? (
          <InteractiveHand
            hand={humanPlayer.hand}
            legalActionsByCard={legalActionsByCard}
            isPending={isPending}
            onPlayLand={handlePlayLand}
            onCastSpell={handleCastSpell}
            onDragStart={setDraggedCardId}
            onDragEnd={() => setDraggedCardId(null)}
          />
        ) : (
          <div style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {humanPlayer.hand.length} card{humanPlayer.hand.length !== 1 ? 's' : ''} in hand
          </div>
        )}
      </div>

      {/* Action log sidebar */}
      <div className="action-log-container">
        <ActionLog gameId={gs.game_id} />
      </div>

      {/* Floating action panel */}
      <ActionPanel
        isMyTurn={isMyTurn}
        phase={phase}
        step={step}
        legalActions={legalActions}
        selectedAttackers={selectedAttackers}
        hasBlockerAssignments={blockerAssignments.size > 0}
        autoPassPriority={autoPassPriority}
        isPending={isPending}
        lastError={lastError}
        isResponseWindow={isResponseWindow}
        onPassPriority={handlePassPriority}
        onConfirmAttackers={handleConfirmAttackers}
        onConfirmBlockers={handleConfirmBlockers}
        onToggleAutoPass={handleToggleAutoPass}
        onClearError={clearError}
      />

      {/* Modals */}
      {pendingCast && gs && (
        <TargetChoiceModal
          action={pendingCast.action}
          cardName={gs.players.flatMap(p => p.hand).find(c => c.id === pendingCast.cardId)?.name ?? 'Spell'}
          onConfirm={handleCastConfirm}
          onCancel={() => setPendingCast(null)}
        />
      )}
      {isMyTurn && isMulliganPhase && (
        <MulliganModal
          hand={humanPlayer.hand}
          onKeep={() => keepAction && submitAction('mulligan', { player_name: humanPlayer.name, keep: true })}
          onMulligan={() => doMulliganAction && submitAction('mulligan', { player_name: humanPlayer.name, keep: false })}
        />
      )}
      {isMyTurn && isDiscardPhase && (
        <DiscardModal
          hand={humanPlayer.hand}
          count={discardActions.length}
          onDiscard={(cardId) => submitAction('discard', { card_id: cardId })}
        />
      )}

      {/* Game result overlay */}
      {!_gameOverDismissed && (
        <GameResultOverlay
          isGameOver={gs.is_game_over}
          winner={gs.winner}
          humanPlayerName={humanPlayer.name}
          gameId={gs.game_id}
        />
      )}
    </div>
  )
}
