"""
Player action type hierarchy.
PLA-01: All player decision types modeled with validation.

Provides a unified representation of every action a player can take,
usable by the AI system, logging/transcripts, and legal action rendering.
"""
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class PlayerActionType(str, Enum):
    """All action types a player can take during a game."""
    CAST_SPELL = "cast_spell"
    ACTIVATE_ABILITY = "activate_ability"
    PLAY_LAND = "play_land"
    DECLARE_ATTACKERS = "declare_attackers"
    DECLARE_BLOCKERS = "declare_blockers"
    ORDER_BLOCKERS = "order_blockers"
    ASSIGN_COMBAT_DAMAGE = "assign_combat_damage"
    PASS_PRIORITY = "pass_priority"
    PUT_TRIGGER_ON_STACK = "put_trigger"
    DECLINE_TRIGGER = "decline_trigger"
    MULLIGAN = "declare_mulligan"
    CHOOSE = "choose"
    ACTIVATE_LOYALTY = "activate_loyalty"
    CASCADE_CHOICE = "cascade_choice"
    CREW = "crew"
    TURN_FACE_UP = "turn_face_up"
    FORETELL = "foretell"
    CAST_FORETOLD = "cast_foretold"
    SPECIAL_ACTION = "special_action"
    CONCEDE = "concede"


class PlayerAction(BaseModel):
    """
    Unified representation of a player action.

    This model wraps any of the specific action request types (CastRequest,
    ActivateRequest, etc.) into a single structure with type discrimination,
    making it suitable for serialization, AI consumption, and logging.
    """
    action_type: PlayerActionType
    player_name: str
    game_id: str = ""
    card_id: Optional[str] = None
    permanent_id: Optional[str] = None
    targets: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class ActionValidationResult(BaseModel):
    """Result of validating whether a player action is legal."""
    is_legal: bool
    reason: str = ""
    action: Optional[PlayerAction] = None


class PlayerActionLog(BaseModel):
    """
    A logged player action with timing information.
    Used for game transcripts and AI training data.
    """
    action: PlayerAction
    turn: int
    phase: str
    step: str
    priority_number: int = 0
    timestamp: float = 0.0
    legal: bool = True
