import hashlib
import uuid
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field



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


class ManaPool(BaseModel):
    W: int = 0
    U: int = 0
    B: int = 0
    R: int = 0
    G: int = 0
    C: int = 0  # generic colorless


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
    # Commander format
    command_zone: list[Card] = Field(default_factory=list)
    commander_name: Optional[str] = None
    commander_cast_count: int = 0


class PendingTrigger(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_permanent_id: str
    controller: str
    trigger_type: str
    effect_description: str
    source_card_name: str


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
