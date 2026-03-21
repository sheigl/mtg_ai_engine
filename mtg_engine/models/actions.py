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


class LegalActionsResponse(BaseModel):
    priority_player: str
    phase: str
    step: str
    legal_actions: list[LegalAction]


class ErrorResponse(BaseModel):
    error: str
    error_code: str
