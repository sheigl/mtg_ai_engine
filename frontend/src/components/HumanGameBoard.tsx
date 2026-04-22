import { useState, useEffect, useCallback, useRef } from 'react'
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
import { DebugPanel } from './DebugPanel'
import type { GameState, Permanent } from '../types/game'
import '../styles/board.css'
import '../styles/debug.css'

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

  const [humanPlayerName, setHumanPlayerName] = useState<string>(() => {
    const fromNav = (location.state as { humanPlayerName?: string } | null)?.humanPlayerName
    if (fromNav) {
      localStorage.setItem(`hgb-player-${gameId}`, fromNav)
      return fromNav
    }
    return localStorage.getItem(`hgb-player-${gameId}`) ?? ''
  })

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

  const [selectedAttackers, setSelectedAttackers] = useState<Set<string>>(new Set())
  const [blockerAssignments, setBlockerAssignments] = useState<Map<string, string>>(new Map())
  const [pendingCast, setPendingCast] = useState<{ action: LegalAction; cardId: string } | null>(null)
  const [autoPassPriority, setAutoPassPriority] = useState(() => {
    const stored = localStorage.getItem('hgb-auto-pass')
    return stored === null ? true : stored === 'true'
  })
  const [_gameOverDismissed] = useState(false)
  const [draggedCardId, setDraggedCardId] = useState<string | null>(null)

  const [handOrder, setHandOrder] = useState<string[]>([])
  const [permanentOrder, setPermanentOrder] = useState<string[]>([])
  const handOrderRef = useRef(handOrder)
  const permanentOrderRef = useRef(permanentOrder)
  handOrderRef.current = handOrder
  permanentOrderRef.current = permanentOrder

  useEffect(() => {
    if (step !== 'declare_attackers') setSelectedAttackers(new Set())
    if (step !== 'declare_blockers') setBlockerAssignments(new Map())
  }, [step])

  useEffect(() => {
    if (!isMyTurn || !autoPassPriority || isPending) return
    if (legalActions.length === 1 && legalActions[0].action_type === 'pass') {
      const timer = setTimeout(() => submitAction('pass', {}), 300)
      return () => clearTimeout(timer)
    }
  }, [isMyTurn, autoPassPriority, isPending, legalActions, submitAction])

  useEffect(() => {
    if (!gs || !humanPlayerName) return
    const human = gs.players.find(p => p.name === humanPlayerName) ?? gs.players[0]
    if (!human) return
    const handIds = new Set(human.hand.map(c => c.id))
    setHandOrder(prev => {
      const kept = prev.filter(id => handIds.has(id))
      const newIds = human.hand.map(c => c.id).filter(id => !prev.includes(id))
      return [...kept, ...newIds]
    })
    const permIds = new Set(gs.battlefield.filter(p => p.controller === humanPlayerName).map(p => p.id))
    setPermanentOrder(prev => {
      const kept = prev.filter(id => permIds.has(id))
      const newIds = [...permIds].filter(id => !prev.includes(id))
      return [...kept, ...newIds]
    })
  }, [gs, humanPlayerName])

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
        x_value: 0,
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
      x_value: xValue ?? 0,
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
    const declareAction = legalActions.find(a => a.action_type === 'declare_attackers')
    const defendingId = declareAction?.card_name ?? ''
    submitAction('declare_attackers', {
      attack_declarations: [...selectedAttackers].map(attacker_id => ({
        attacker_id,
        defending_id: defendingId,
      })),
    })
  }, [submitAction, selectedAttackers, legalActions])

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
    submitAction('declare_blockers', {
      block_declarations: [...blockerAssignments.entries()].map(([blocker_id, attacker_id]) => ({
        blocker_id,
        attacker_id,
      })),
    })
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

  const mulliganActions = legalActions.filter(a => a.action_type === 'declare_mulligan')
  const isMulliganPhase = mulliganActions.length > 0
  const keepAction = mulliganActions.find(a => a.description?.toLowerCase().includes('keep'))
  const doMulliganAction = mulliganActions.find(a => !a.description?.toLowerCase().includes('keep'))

  const discardActions = legalActions.filter(a => a.action_type === 'discard')
  const isDiscardPhase = discardActions.length > 0 && legalActions.every(a => a.action_type === 'discard')

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

  if (isLoading || !gs || !humanPlayerName) {
    return (
      <div className="center-message">
        <div className="spinner" style={{ marginBottom: 'var(--space-4)' }} />
        <span style={{ color: 'var(--text-secondary)' }}>Loading game...</span>
      </div>
    )
  }

  const humanPlayer = gs.players.find(p => p.name === humanPlayerName) ?? gs.players[0]
  const opponentPlayer = gs.players.find(p => p.name !== humanPlayerName) ?? gs.players[1]
  const humanPermanents = getPlayerPermanents(gs, humanPlayer.name)
  const opponentPermanents = getPlayerPermanents(gs, opponentPlayer.name)
  const isCommander = gs.format === 'commander'

  const legalBlockerIds = new Set(
    getCreatures(humanPermanents)
      .filter(p => !p.tapped)
      .map(p => p.id),
  )

  const attackingCreatures = getAttackingCreatures(gs)
  const isResponseWindow = isMyTurn && gs.active_player !== humanPlayer.name

  return (
    <div className="game-board with-sidebar">
      <div className="board-actions">
        <button className="btn btn--secondary btn--sm" onClick={() => navigate('/')}>← Games</button>
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

      {/* Human battlefield */}
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
        <Battlefield
          permanents={humanPermanents}
          permanentOrder={permanentOrder}
          onReorder={setPermanentOrder}
          isPending={isPending}
        />
      </div>

      {/* Blocker assigner */}
      {isMyTurn && step === 'declare_blockers' && attackingCreatures.length > 0 && (
        <div className="blocker-overlay">
          <BlockerAssigner
            myCreatures={getCreatures(humanPermanents)}
            attackingCreatures={attackingCreatures}
            assignments={blockerAssignments}
            legalBlockerIds={legalBlockerIds}
            isPending={isPending}
            onAssign={handleAssignBlocker}
            onUnassign={handleUnassignBlocker}
          />
        </div>
      )}

      {/* Human hand */}
      <div>
        <PlayerZone
          player={humanPlayer}
          isActive={gs.active_player === humanPlayer.name}
          format={gs.format}
          commanderDamage={isCommander ? gs.commander_damage[humanPlayer.name] : undefined}
        />
        <InteractiveHand
          hand={humanPlayer.hand}
          legalActionsByCard={isMyTurn ? legalActionsByCard : new Map()}
          isPending={isPending}
          handOrder={handOrder}
          onReorder={setHandOrder}
          onPlayLand={handlePlayLand}
          onCastSpell={handleCastSpell}
          onDragStart={setDraggedCardId}
          onDragEnd={() => setDraggedCardId(null)}
        />
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
        eligibleAttackers={step === 'declare_attackers' ? getCreatures(humanPermanents)
          .filter(p => !p.tapped && !p.summoning_sick)
          .map(p => ({ id: p.id, name: p.card.name, power: p.card.power ?? '?', toughness: p.card.toughness ?? '?' })) : undefined}
        onPassPriority={handlePassPriority}
        onConfirmAttackers={handleConfirmAttackers}
        onConfirmBlockers={handleConfirmBlockers}
        onToggleAutoPass={handleToggleAutoPass}
        onClearError={clearError}
        onToggleAttacker={handleToggleAttacker}
      />

      {/* Modals */}
      {pendingCast && gs && (
        <TargetChoiceModal
          action={pendingCast.action}
          cardName={gs.players.flatMap(p => p.hand).find(c => c.id === pendingCast.cardId)?.name ?? 'Spell'}
          targetNames={new Map([
            ...gs.battlefield.map(p => [p.id, `${p.card.name} (${p.controller})`] as [string, string]),
            ...gs.players.map(p => [p.name, p.name] as [string, string]),
          ])}
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

      <DebugPanel gameId={gs.game_id} isGameOver={gs.is_game_over} debugEnabled={gs.debug_enabled} />
    </div>
  )
}
