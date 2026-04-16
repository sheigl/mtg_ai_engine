from typing import Optional, Any
from pydantic import BaseModel, Field


# --- Attack/Block declarations ---

class AttackDeclaration(BaseModel):
    attacker_id: str
    defending_id: str  # player name or planeswalker permanent ID


class BlockDeclaration(BaseModel):
    blocker_id: str
    attacker_id: str


class BlockerOrdering(BaseModel):
    attacker_id: str
    blocker_order: list[str]  # ordered blocker permanent IDs


class DamageAssignment(BaseModel):
    source_id: str   # attacker or blocker permanent ID
    target_id: str   # permanent ID or player name
    damage: int


# --- Action request bodies ---

class CastRequest(BaseModel):
    card_id: str
    targets: list[str] = Field(default_factory=list)
    mana_payment: dict[str, int] = Field(default_factory=dict)
    alternative_cost: Optional[str] = None
    modes_chosen: list[int] = Field(default_factory=list)
    dry_run: bool = False
    from_command_zone: bool = False
    from_graveyard: bool = False
    # New fields for 018 feature
    x_value: int = 0                          # X value chosen for {X} mana cost
    kicker_paid: bool = False                  # Whether to pay kicker cost
    jump_start_discard_id: Optional[str] = None   # Card to discard for jump-start
    # New fields for 019 feature (keyword mana cost modifiers)
    convoke_creature_ids: list[str] = Field(default_factory=list)  # Creatures to tap for Convoke
    delve_card_ids: list[str] = Field(default_factory=list)        # Cards to exile from graveyard for Delve
    improvise_artifact_ids: list[str] = Field(default_factory=list)  # Artifacts to tap for Improvise
    emerge_sacrifice_id: Optional[str] = None                       # Creature to sacrifice for Emerge
    opponent_target: Optional[str] = None                           # Disambiguate "target opponent" in 3+ player games
    # US4, US17, US18, US29, US30: Multi-face and special cast types
    face_index: int = 0
    fuse: bool = False
    as_face_down: bool = False
    foretell: bool = False
    cast_foretold: bool = False
    mutate_target_id: Optional[str] = None
    mutate_on_top: bool = True


class ActivateRequest(BaseModel):
    permanent_id: str
    ability_index: int
    targets: list[str] = Field(default_factory=list)
    mana_payment: dict[str, int] = Field(default_factory=dict)
    dry_run: bool = False


class PlayLandRequest(BaseModel):
    card_id: str
    dry_run: bool = False


class DeclareAttackersRequest(BaseModel):
    attack_declarations: list[AttackDeclaration]
    dry_run: bool = False


class DeclareBlockersRequest(BaseModel):
    block_declarations: list[BlockDeclaration]
    dry_run: bool = False


class OrderBlockersRequest(BaseModel):
    orderings: list[BlockerOrdering]
    dry_run: bool = False


class AssignCombatDamageRequest(BaseModel):
    assignments: list[DamageAssignment]
    dry_run: bool = False


class ChoiceRequest(BaseModel):
    choice_id: str
    selection: Any
    dry_run: bool = False


class PassRequest(BaseModel):
    dry_run: bool = False


class PutTriggerRequest(BaseModel):
    trigger_id: str
    targets: list[str] = Field(default_factory=list)
    dry_run: bool = False


class SpecialActionRequest(BaseModel):
    action_type: str  # "play_face_down" | "turn_face_up" | "suspend" | etc.
    card_id: Optional[str] = None
    permanent_id: Optional[str] = None
    targets: list[str] = Field(default_factory=list)
    dry_run: bool = False


# --- New request models for US16, US17, US29 ---

class CrewRequest(BaseModel):
    """Request to crew a vehicle. US16."""
    permanent_id: str  # Vehicle permanent ID
    creature_ids: list[str]  # Untapped creatures to tap as crew


class TurnFaceUpRequest(BaseModel):
    """Request to turn a morph face up. US17."""
    permanent_id: str
    mana_payment: dict[str, int] = Field(default_factory=dict)


class ForetellRequest(BaseModel):
    """Request to foretell a card. US29."""
    card_id: str


# --- Response models ---

class LegalAction(BaseModel):
    action_type: str
    card_id: Optional[str] = None
    card_name: Optional[str] = None
    permanent_id: Optional[str] = None
    ability_index: Optional[int] = None
    valid_targets: list[str] = Field(default_factory=list)
    mana_options: list[dict] = Field(default_factory=list)
    description: Optional[str] = None
    # Extended fields for new action types (017-forge-ai-parity)
    loyalty_ability_index: Optional[int] = None   # activate_loyalty: which ability index
    cascade_card_id: Optional[str] = None          # cascade_choice: the card being offered
    from_graveyard: bool = False                   # cast originating from graveyard zone
    # New fields for 018 feature
    x_value: Optional[int] = None         # For X spell variants
    kicker_paid: Optional[bool] = None    # For kicker variants
    # US4, US16, US17, US18, US29, US30, US3: New action types
    face_index: Optional[int] = None      # cast_split_left/right, cast_adventure
    fuse: Optional[bool] = None           # cast_fuse
    new_action_type: Optional[str] = None # "crew", "turn_face_up", "foretell", "cast_foretold", "cast_adventure", "activate_mana_ability", "mutate"


# --- New request models for Forge AI parity (017) ---

class MulliganRequest(BaseModel):
    """London mulligan decision request."""
    player_name: str
    keep: bool  # True = keep hand, False = discard and draw hand_size-1


class ActivateLoyaltyRequest(BaseModel):
    """Activate a planeswalker loyalty ability."""
    permanent_id: str    # planeswalker permanent ID
    ability_index: int   # 0 = first ability (usually +), 1 = second, 2 = ultimate
    targets: list[str] = Field(default_factory=list)


class CascadeChoiceRequest(BaseModel):
    """Resolve a cascade trigger — cast the offered card or skip."""
    player_name: str
    card_id: str    # the cascaded card being offered
    cast: bool      # True = cast it for free, False = exile it and skip


class CopySpellRequest(BaseModel):
    """Request to copy a spell currently on the stack. US7 (014)."""
    player_name: str
    target_stack_id: str   # ID of the stack object to copy
    new_targets: list[str] = Field(default_factory=list)


class LegalActionsResponse(BaseModel):
    priority_player: str
    phase: str
    step: str
    legal_actions: list[LegalAction]


class ErrorResponse(BaseModel):
    error: str
    error_code: str
