import type { Phase, Step } from '../types/game'
import '../styles/board.css'

interface PhaseTrackerProps {
  turn: number
  phase: Phase
  step: Step
  activePlayer: string
}

const PHASE_LABELS: Record<Phase, string> = {
  beginning: 'Beginning',
  precombat_main: 'Main 1',
  combat: 'Combat',
  postcombat_main: 'Main 2',
  ending: 'End',
}

const STEP_LABELS: Record<Step, string> = {
  untap: 'Untap',
  upkeep: 'Upkeep',
  draw: 'Draw',
  main: 'Main',
  beginning_of_combat: 'Begin Combat',
  declare_attackers: 'Attackers',
  declare_blockers: 'Blockers',
  first_strike_damage: 'First Strike',
  combat_damage: 'Damage',
  end_of_combat: 'End Combat',
  end: 'End Step',
  cleanup: 'Cleanup',
}

export function PhaseTracker({ turn, phase, step, activePlayer }: PhaseTrackerProps) {
  return (
    <div className="phase-tracker">
      <span className="turn-counter">Turn {turn}</span>
      <span className={`phase-badge ${phase}`}>
        {PHASE_LABELS[phase]}
      </span>
      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
        {STEP_LABELS[step]}
      </span>
      <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
        — {activePlayer}'s turn
      </span>
    </div>
  )
}
