import hashlib
import uuid
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class DamageModifier(BaseModel):
    """A damage multiplication replacement effect (CR 614.1a)."""
    source_permanent_id: str        # Permanent providing the effect
    controller: str                 # Controller of the source permanent
    multiplier: int = 2             # 2 = double, 3 = triple
    applies_to: str = "all"         # "all" | "sources_you_control" | "combat_only"
    timestamp: float = 0.0          # For ordering when multiple modifiers apply

class ManaPoolPersistence(BaseModel):
    """Tracks which mana colors persist across step/phase transitions."""
    colors: list[str] = Field(default_factory=list)  # ["G"] for Omnath, ["W","U","B","R","G","C"] for Upwelling
    convert_to_colorless: bool = False                # True for Kruphix (unused mana becomes colorless)

class Phase(str, Enum):
    BEGINNING = "beginning"
    PRECOMBAT_MAIN = "precombat_main"
    COMBAT = "combat"
    POSTCOMBAT_MAIN = "postcombat_main"
    ENDING = "ending"

class Step(str, Enum):
    UNTAP = "untap"
    UPKEEP = "upkeep"
    DRAW = "draw"
    MAIN = "main"
    BEGINNING_OF_COMBAT = "beginning_of_combat"
    DECLARE_ATTACKERS = "declare_attackers"
    DECLARE_BLOCKERS = "declare_blockers"
    FIRST_STRIKE_DAMAGE = "first_strike_damage"
    COMBAT_DAMAGE = "combat_damage"
    END_OF_COMBAT = "end_of_combat"
    END = "end"
    CLEANUP = "cleanup"


class CardFace(BaseModel):
    name: str
    mana_cost: Optional[str] = None
    type_line: str = ""
    oracle_text: Optional[str] = None
    power: Optional[str] = None
    toughness: Optional[str] = None
    loyalty: Optional[str] = None
    colors: list[str] = Field(default_factory=list)


class Card(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scryfall_id: Optional[str] = None
    name: str
    mana_cost: Optional[str] = None
    type_line: str = ""
    oracle_text: Optional[str] = None
    power: Optional[str] = None
    toughness: Optional[str] = None
    loyalty: Optional[str] = None
    colors: list[str] = Field(default_factory=list)
    color_identity: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    faces: Optional[list[CardFace]] = None
    cmc: float = 0.0
    parse_status: str = "ok"  # "ok" | "unsupported"
    card_layout: str = "normal" # "normal", "split", "mdfc", "adventure", "aftermath", "transform"
    # US23: Snow supertype for snow mana tracking
    supertypes: list[str] = Field(default_factory=list)


class ManaPool(BaseModel):
    W: int = 0
    U: int = 0
    B: int = 0
    R: int = 0
    G: int = 0
    C: int = 0  # generic colorless
    # US23: Snow mana tracking for {S} costs
    snow: int = 0
    snow_by_color: dict[str, int] = Field(default_factory=dict)


class Permanent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    card: Card
    controller: str
    tapped: bool = False
    damage_marked: int = 0
    counters: dict[str, int] = Field(default_factory=dict)
    attached_to: Optional[str] = None
    attachments: list[str] = Field(default_factory=list)
    is_token: bool = False
    turn_entered_battlefield: int = 0
    summoning_sick: bool = True
    is_face_down: bool = False
    timestamp: float = 0.0  # for layer system ordering (CR 613.7)
    copy_of_permanent_id: Optional[str] = None  # layer 1 copy effects (014)
    # Temporary P/T bonuses from "until end of turn" effects (layer 7c)
    power_bonus: int = 0
    toughness_bonus: int = 0
    # US23: Effect expiry scope — "end_of_turn" or "player:<name>" for "until your next turn"
    power_bonus_expires: Optional[str] = None
    toughness_bonus_expires: Optional[str] = None
    # Planeswalker loyalty tracking (017-forge-ai-parity)
    loyalty: int = 0
    loyalty_activated_this_turn: bool = False
    # New fields for 018 feature
    unearthed: bool = False     # True if entered via Unearth — exile at end of turn
    time_counters: int = 0      # Used for suspended cards in exile zone
    foretold: bool = False      # True if exiled face-down via Foretell
    regen_shields: int = 0      # CR 701.15: active regeneration shields
    # US15: Phasing
    phased_out: bool = False
    # US16: Vehicles
    crewed_until_end_of_turn: bool = False
    # US15: Phasing
    has_phasing: bool = False
    # US27: Echo
    echo_paid: bool = False
    echo_cost: Optional[str] = None
    # US30: Mutate
    mutated_cards: list[Card] = Field(default_factory=list)
    # US19: Mana persistence
    mana_doesnt_empty: Optional[ManaPoolPersistence] = None


class StackObject(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_card: Card
    controller: str
    targets: list[str] = Field(default_factory=list)
    effects: list[str] = Field(default_factory=list)
    is_copy: bool = False
    modes_chosen: list[int] = Field(default_factory=list)
    alternative_cost: Optional[str] = None
    mana_payment: dict[str, int] = Field(default_factory=dict)
    # New fields for 018 feature
    x_value: int = 0                          # X value for {X} spells
    kicker_paid: bool = False                  # Whether kicker cost was paid
    jump_start_discard_id: Optional[str] = None   # Card discarded for jump-start cost
    uncounterable: bool = False               # CR 702.102: spell cannot be countered
    # New fields for 019 feature (stack mechanics)
    buyback_paid: bool = False                 # CR 702.27: Whether buyback cost was paid
    replicate_count: int = 0                   # CR 702.87: Number of times to replicate
    flashback: bool = False                    # CR 702.32: Whether cast via flashback from graveyard
    escape: bool = False                       # CR 702.132: Whether cast via escape from graveyard
    metadata: dict = Field(default_factory=dict)  # Arbitrary per-spell metadata (e.g. grant_haste)
    # US4, US17, US18, US30: Multi-face and special cast types
    face_index: int = 0
    is_face_down: bool = False
    is_adventure: bool = False
    is_fused: bool = False
    is_foretold: bool = False
    mutate_target_id: Optional[str] = None
    mutate_on_top: bool = True


class Emblem(BaseModel):
    """
    A planeswalker emblem. CR 113.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    controller: str  # Player name who controls this emblem
    source_planeswalker: str  # Name of planeswalker that created this emblem
    abilities: list[str] = Field(default_factory=list)  # Ability text lines


class PlayerState(BaseModel):
    name: str
    life: int = 20
    hand: list[Card] = Field(default_factory=list)
    library: list[Card] = Field(default_factory=list)  # index 0 = top
    graveyard: list[Card] = Field(default_factory=list)
    exile: list[Card] = Field(default_factory=list)
    poison_counters: int = 0
    mana_pool: ManaPool = Field(default_factory=ManaPool)
    lands_played_this_turn: int = 0
    has_lost: bool = False
    max_hand_size: int = 7
    # Deck identity (033-deck-randomizer)
    deck_name: Optional[str] = None
    color_identity: list[str] = Field(default_factory=list)
    # Commander format
    command_zone: list[Card] = Field(default_factory=list)
    commander_name: Optional[str] = None
    commander_cast_counts: dict[str, int] = Field(default_factory=dict)  # keyed by card name (partner support)
    # New fields for 018 feature
    suspended_cards: list[Card] = Field(default_factory=list)   # Cards exiled via Suspend (with time_counters)
    foretold_cards: list[Card] = Field(default_factory=list)    # Cards exiled face-down via Foretell
    # US19: Mana persistence
    mana_persistence: ManaPoolPersistence = Field(default_factory=ManaPoolPersistence)
    # US29: Foretell tracking
    exile_by: str = ""  # Track how card entered exile ("foretell", "adventure", etc.)
    foretold_turns: dict[str, int] = Field(default_factory=dict)  # card_id -> turn when foretold
    # US18: Adventure — exiled adventure spell cards whose creature half can be cast
    adventure_cards: list[Card] = Field(default_factory=list)


class PendingTrigger(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_permanent_id: str
    controller: str
    trigger_type: str
    effect_description: str
    source_card_name: str
    is_optional: bool = False  # CR 603.3: "you may" triggers offer a choice


class DamagePreventionEffect(BaseModel):
    """An active damage prevention shield. CR 614.1."""
    effect_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_permanent_id: Optional[str] = None
    target_id: Optional[str] = None   # None = global (all combat)
    remaining: Optional[int] = None   # None = unlimited (until end of turn)
    combat_only: bool = False
    color_restriction: Optional[str] = None  # prevents damage only from this color source


class AttackConstraint(BaseModel):
    """A constraint on declaring attackers (Propaganda, goad, must-attack). CR 508."""
    source_id: str
    affected_id: str   # permanent ID or "all"
    constraint_type: str  # "must_attack" | "cannot_attack" | "cost_to_attack" | "goad"
    cost: Optional[str] = None          # mana cost string for cost_to_attack
    goad_controller: Optional[str] = None  # for goad: player whose creatures must be attacked


class BlockConstraint(BaseModel):
    """A constraint on declaring blockers (can't block, evasion). CR 509."""
    source_id: str
    affected_id: str   # permanent ID or "all"
    constraint_type: str  # "cannot_block" | "can_only_block_flyers" | "min_power_to_block"
    restriction: Optional[str] = None


class AttackerInfo(BaseModel):
    permanent_id: str
    defending_id: str   # player name or planeswalker permanent ID
    is_blocked: bool = False
    blocker_ids: list[str] = Field(default_factory=list)
    blocker_order: list[str] = Field(default_factory=list)  # damage assignment order


class CombatState(BaseModel):
    attackers: list[AttackerInfo] = Field(default_factory=list)
    # Map blocker_id → attacker_id it is blocking
    blocker_assignments: dict[str, str] = Field(default_factory=dict)
    first_strike_done: bool = False   # True after first-strike damage step
    damage_assigned: bool = False     # True once assign_combat_damage called this step; reset on step change
    blockers_declared: bool = False   # True once declare_blockers called; reset on step change


class GameState(BaseModel):
    game_id: str
    seed: int
    turn: int = 1
    active_player: str
    phase: Phase = Phase.BEGINNING
    step: Step = Step.UNTAP
    priority_holder: str
    stack: list[StackObject] = Field(default_factory=list)
    battlefield: list[Permanent] = Field(default_factory=list)
    players: list[PlayerState]
    pending_triggers: list[PendingTrigger] = Field(default_factory=list)
    state_hash: str = ""
    is_game_over: bool = False
    winner: Optional[str] = None
    combat: Optional[CombatState] = None
    # Series mode (032-game-series)
    series_id: Optional[str] = None
    # Human player name for resume (034-game-persistence)
    human_player_name: Optional[str] = None
    # AI player config for restarting loop on restore
    ai_player_type: Optional[str] = None
    ai_player_name: Optional[str] = None
    ai_base_url: Optional[str] = None
    ai_model: Optional[str] = None
    ai_enable_thinking: Optional[bool] = None
    # Commander format
    format: str = "standard"
    commander_damage: dict[str, dict[str, int]] = Field(default_factory=dict)
    # Rules engine completeness (014)
    prevention_effects: list[DamagePreventionEffect] = Field(default_factory=list)
    attack_constraints: list[AttackConstraint] = Field(default_factory=list)
    block_constraints: list[BlockConstraint] = Field(default_factory=list)
    prevent_all_combat_damage: bool = False
    phase_skip_flags: dict[str, bool] = Field(default_factory=dict)
    debug_enabled: bool = False
    # Mulligan phase (017-forge-ai-parity)
    mulligan_phase_active: bool = False
    hands_mulliganed: dict[str, int] = Field(default_factory=dict)
    players_kept: list[str] = Field(default_factory=list)
    # Cascade pending choice (017-forge-ai-parity)
    pending_cascade: Optional[dict] = None
    # Pending blocking choices (set by engine, cleared on choice submission)
    pending_scry_choice: Optional[dict] = None
    # Format: {"player": str, "cards": [Card], "n": int}
    pending_surveil_choice: Optional[dict] = None
    # Format: {"player": str, "cards": [Card], "n": int}
    pending_tutor_choice: Optional[dict] = None
    # Format: {"player": str, "filter_type": str, "destination": "hand" | "battlefield"}
    pending_discard_choice: Optional[dict] = None
    # Format: {"player": str, "count": int}
    pending_ward_payment: Optional[dict] = None
    # Format: {"player": str, "ward_cost": str, "targeting_spell_id": str}
    pending_dredge_choice: Optional[dict] = None
    # Format: {"player": str, "dredgeable_cards": [Card], "n": int} (n = dredge number)
    pending_proliferate_choice: Optional[dict] = None
    # Format: {"player": str, "eligible": [{"id": str, "name": str, "counters": dict}]}
    # Transform tracking
    spells_cast_this_turn: int = 0    # Reset each turn; checked for werewolf conditions
    spells_cast_last_turn: int = 0    # Snapshot of previous turn's count
    # Extra turns queue (CR 500.7): LIFO — pop() gives next extra turn recipient
    extra_turns: list[str] = Field(default_factory=list)
    # Delayed triggered abilities (CR 603.7): fire at a future phase/step
    # Each entry: {"phase": str, "step": str|None, "controller": str, "effect": str, "once": bool}
    delayed_triggers: list[dict] = Field(default_factory=list)
    # Planeswalker emblems (CR 113)
    emblems: list[Emblem] = Field(default_factory=list)
    # US10: Additional combat phases
    additional_combat_phases: int = 0
    # US11: Step skipping
    step_skip_flags: dict[str, bool] = Field(default_factory=dict)
    # US14: Damage modifiers
    damage_modifiers: list[DamageModifier] = Field(default_factory=list)
    # US7: Legend rule choice
    pending_legend_choice: Optional[dict] = None
    # US17: Morph payment
    pending_morph_payment: Optional[dict] = None
    # US27: Echo payment
    pending_echo_payment: Optional[dict] = None
    # Transcript for persistence (034-game-persistence)
    transcript_entries: list[dict] = Field(default_factory=list)

    def compute_hash(self) -> str:
        """Compute deterministic hash of state, excluding state_hash itself. REQ-API05"""
        data = self.model_dump()
        data.pop("state_hash", None)
        import json
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def refresh_hash(self) -> "GameState":
        self.state_hash = self.compute_hash()
        return self
