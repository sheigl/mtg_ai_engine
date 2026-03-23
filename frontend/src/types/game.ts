// TypeScript types mirroring engine Pydantic models

export type Phase =
  | 'beginning'
  | 'precombat_main'
  | 'combat'
  | 'postcombat_main'
  | 'ending'

export type Step =
  | 'untap'
  | 'upkeep'
  | 'draw'
  | 'main'
  | 'beginning_of_combat'
  | 'declare_attackers'
  | 'declare_blockers'
  | 'first_strike_damage'
  | 'combat_damage'
  | 'end_of_combat'
  | 'end'
  | 'cleanup'

export interface ManaPool {
  W: number
  U: number
  B: number
  R: number
  G: number
  C: number
}

export interface Card {
  id: string
  scryfall_id: string | null
  name: string
  mana_cost: string | null
  type_line: string
  oracle_text: string | null
  power: string | null
  toughness: string | null
  loyalty: string | null
  colors: string[]
  color_identity: string[]
  keywords: string[]
  cmc: number
  parse_status: string
}

export interface Permanent {
  id: string
  card: Card
  controller: string
  tapped: boolean
  damage_marked: number
  counters: Record<string, number>
  attached_to: string | null
  attachments: string[]
  is_token: boolean
  turn_entered_battlefield: number
  summoning_sick: boolean
  is_face_down: boolean
  timestamp: number
}

export interface StackObject {
  id: string
  source_card: Card
  controller: string
  targets: string[]
  effects: string[]
  is_copy: boolean
  modes_chosen: number[]
  alternative_cost: string | null
  mana_payment: Record<string, number>
}

export interface PlayerState {
  name: string
  life: number
  hand: Card[]
  library: Card[]
  graveyard: Card[]
  exile: Card[]
  poison_counters: number
  mana_pool: ManaPool
  lands_played_this_turn: number
  has_lost: boolean
  max_hand_size: number
  command_zone: Card[]
  commander_name: string | null
  commander_cast_count: number
}

export interface AttackerInfo {
  permanent_id: string
  defending_id: string
  is_blocked: boolean
  blocker_ids: string[]
  blocker_order: string[]
}

export interface CombatState {
  attackers: AttackerInfo[]
  blocker_assignments: Record<string, string>
  first_strike_done: boolean
}

export interface PendingTrigger {
  id: string
  source_permanent_id: string
  controller: string
  trigger_type: string
  effect_description: string
  source_card_name: string
}

export interface GameState {
  game_id: string
  seed: number
  turn: number
  active_player: string
  phase: Phase
  step: Step
  priority_holder: string
  stack: StackObject[]
  battlefield: Permanent[]
  players: PlayerState[]
  pending_triggers: PendingTrigger[]
  state_hash: string
  is_game_over: boolean
  winner: string | null
  combat: CombatState | null
  format: string
  commander_damage: Record<string, Record<string, number>>
  debug_enabled: boolean
}

export interface GameSummary {
  game_id: string
  player1_name: string
  player2_name: string
  format: string
  turn: number
  phase: string
  step: string
  is_game_over: boolean
  winner: string | null
}

export interface TranscriptEntry {
  seq: number
  event_type: string
  description: string
  data: Record<string, unknown>
  turn: number
  phase: string
  step: string
}
