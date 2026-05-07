"""
Timing restrictions for activated abilities.

ACT-02: Determines when abilities may be activated based on game phase/step.

Handles:
- "Activate only as a sorcery" (main phase, priority, empty stack)
- "Activate only during combat" 
- "Activate only during your turn"
- "Activate only during opponent's turn"
- "Any time you could cast an instant"
"""
from __future__ import annotations
import logging
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState

logger = logging.getLogger(__name__)


class TimingRestriction(Enum):
    """When an activated ability may be used."""
    ANY_TIME = "any_time"
    INSTANT_SPEED = "instant_speed"
    SORCERY_SPEED = "sorcery_speed"
    YOUR_MAIN_PHASE = "your_main_phase"
    OPPONENT_TURN = "opponent_turn"
    YOUR_TURN = "your_turn"
    COMBAT_PHASE = "combat_phase"
    DECLARE_ATTACKERS = "declare_attackers"
    DECLARE_BLOCKERS = "declare_blockers"
    DAMAGE_STEP = "damage_step"
    BEGINNING_OF_COMBAT = "beginning_of_combat"
    END_OF_COMBAT = "end_of_combat"
    UPKEEP = "upkeep"
    END_STEP = "end_step"
    CLEANUP = "cleanup"
    LOYALTY_ABILITY = "loyalty_ability"


def can_activate(
    game_state: GameState,
    restriction: TimingRestriction,
    controller: str,
) -> bool:
    """
    Check whether an ability with the given timing restriction can be
    activated right now.

    Args:
        game_state: Current game state.
        restriction: Timing restriction to check.
        controller: Player trying to activate.

    Returns:
        True if activation is legal.
    """
    step = game_state.step.value
    phase = game_state.phase.value
    active = game_state.active_player
    is_active_player = controller == active

    if restriction == TimingRestriction.ANY_TIME:
        return True

    if restriction == TimingRestriction.INSTANT_SPEED:
        # Can activate at any time you have priority
        return True

    if restriction == TimingRestriction.SORCERY_SPEED:
        return _is_sorcery_timing(game_state, controller)

    if restriction == TimingRestriction.YOUR_MAIN_PHASE:
        return phase in ("precombat_main", "postcombat_main") and is_active_player

    if restriction == TimingRestriction.OPPONENT_TURN:
        return not is_active_player

    if restriction == TimingRestriction.YOUR_TURN:
        return is_active_player

    if restriction == TimingRestriction.COMBAT_PHASE:
        return phase == "combat"

    if restriction == TimingRestriction.DECLARE_ATTACKERS:
        return step == "declare_attackers"

    if restriction == TimingRestriction.DECLARE_BLOCKERS:
        return step == "declare_blockers"

    if restriction == TimingRestriction.DAMAGE_STEP:
        return step in ("combat_damage", "first_strike_damage")

    if restriction == TimingRestriction.BEGINNING_OF_COMBAT:
        return step == "beginning_of_combat"

    if restriction == TimingRestriction.END_OF_COMBAT:
        return step == "end_of_combat"

    if restriction == TimingRestriction.UPKEEP:
        return step == "upkeep"

    if restriction == TimingRestriction.END_STEP:
        return step == "end"

    if restriction == TimingRestriction.CLEANUP:
        return step == "cleanup"

    if restriction == TimingRestriction.LOYALTY_ABILITY:
        return _is_loyalty_timing(game_state, controller)

    return True


def _is_sorcery_timing(game_state: GameState, controller: str) -> bool:
    """
    Sorcery speed: your main phase, stack empty, you have priority.
    CR 307: You may cast a sorcery spell only during your own turn,
    during the main phase, when the stack is empty.
    """
    if controller != game_state.active_player:
        return False
    if game_state.phase.value not in ("precombat_main", "postcombat_main"):
        return False
    if game_state.stack:
        return False
    return True


def _is_loyalty_timing(game_state: GameState, controller: str) -> bool:
    """
    Loyalty abilities can be activated at sorcery speed.
    CR 606.3: A player may activate a loyalty ability of a permanent
    they control any time they have priority and the stack is empty
    during a main phase of their turn.
    """
    return _is_sorcery_timing(game_state, controller)


def parse_timing_restriction(text: str) -> TimingRestriction:
    """
    Parse timing restriction text into a TimingRestriction enum.

    Handles common patterns:
    - "(Activate only as a sorcery.)"
    - "(Activate only during your turn.)"
    - "(Activate only during an opponent's turn.)"
    - "(Activate only during combat.)"
    """
    lower = text.lower().strip().strip("().")

    if "as a sorcery" in lower:
        return TimingRestriction.SORCERY_SPEED
    if "during your turn" in lower:
        return TimingRestriction.YOUR_TURN
    if "during opponent" in lower or "opponent's turn" in lower:
        return TimingRestriction.OPPONENT_TURN
    if "during combat" in lower:
        return TimingRestriction.COMBAT_PHASE
    if "main phase" in lower:
        return TimingRestriction.YOUR_MAIN_PHASE
    if "declare attackers" in lower:
        return TimingRestriction.DECLARE_ATTACKERS
    if "declare blockers" in lower:
        return TimingRestriction.DECLARE_BLOCKERS
    if "damage" in lower:
        return TimingRestriction.DAMAGE_STEP
    if "beginning of combat" in lower:
        return TimingRestriction.BEGINNING_OF_COMBAT
    if "end of combat" in lower:
        return TimingRestriction.END_OF_COMBAT
    if "upkeep" in lower:
        return TimingRestriction.UPKEEP
    if "end step" in lower:
        return TimingRestriction.END_STEP

    return TimingRestriction.ANY_TIME


def get_current_timing(game_state: GameState) -> str:
    """Return human-readable current timing."""
    return f"{game_state.phase.value}/{game_state.step.value}"
