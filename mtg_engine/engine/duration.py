"""
Effect duration tracking. REP-03.
CR 611.3: Duration of continuous effects.
Tracks "until end of turn" and "until your next turn" effects.
"""
import logging

from mtg_engine.models.game import GameState, DurationEffect

logger = logging.getLogger(__name__)


def create_duration_effect(
    game_state: GameState,
    controller: str,
    expires: str = "end_of_turn",
    target_id: str | None = None,
    source_permanent_id: str | None = None,
    description: str = "",
) -> GameState:
    """
    Create a duration-tracked effect. CR 611.3.

    Args:
        game_state: Current game state
        controller: Player controlling the effect
        expires: Expiry scope ("end_of_turn" or "player:<name>")
        target_id: Target permanent ID
        source_permanent_id: Source permanent ID
        description: Human-readable description

    Returns:
        Updated game state with duration effect added.
    """
    effect = DurationEffect(
        controller=controller,
        expires=expires,
        target_id=target_id,
        source_permanent_id=source_permanent_id,
        description=description or f"Duration effect for {controller}",
    )
    game_state.duration_effects.append(effect)
    logger.info(
        "Duration effect created: expires=%s, target=%s",
        expires, target_id,
    )
    return game_state


def check_expired_effects(
    game_state: GameState,
    expiry_scope: str = "end_of_turn",
) -> list[DurationEffect]:
    """
    Check which effects have expired.

    Args:
        game_state: Current game state
        expiry_scope: Expiry scope to check

    Returns:
        List of expired effects.
    """
    expired = [
        eff for eff in game_state.duration_effects
        if eff.expires == expiry_scope
    ]
    if expired:
        logger.info(
            "Found %d expired effects (scope: %s)",
            len(expired), expiry_scope,
        )
    return expired


def remove_expired_effects(
    game_state: GameState,
    expiry_scope: str = "end_of_turn",
) -> GameState:
    """
    Remove expired effects from game state.

    Args:
        game_state: Current game state
        expiry_scope: Expiry scope to remove

    Returns:
        Updated game state with expired effects removed.
    """
    before = len(game_state.duration_effects)
    game_state.duration_effects[:] = [
        eff for eff in game_state.duration_effects
        if eff.expires != expiry_scope
    ]
    removed = before - len(game_state.duration_effects)
    if removed:
        logger.info("Removed %d expired duration effects (scope: %s)", removed, expiry_scope)
    return game_state


def get_active_effects_for_target(
    game_state: GameState,
    target_id: str,
) -> list[DurationEffect]:
    """
    Get all active duration effects targeting a specific permanent.

    Args:
        game_state: Current game state
        target_id: Target permanent ID

    Returns:
        List of active effects for the target.
    """
    return [
        eff for eff in game_state.duration_effects
        if eff.target_id == target_id
    ]


def get_active_effects_for_controller(
    game_state: GameState,
    controller: str,
) -> list[DurationEffect]:
    """
    Get all active duration effects controlled by a player.

    Args:
        game_state: Current game state
        controller: Player name

    Returns:
        List of active effects for the controller.
    """
    return [
        eff for eff in game_state.duration_effects
        if eff.controller == controller
    ]
