"""
Monarch mechanic (MON-01).
CR 103.5a, 702.147: the Monarch.

- When a creature deals combat damage to the monarch, the attacker's controller
  becomes the monarch.
- At the beginning of the monarch's end step, they draw a card.
"""
import logging

from mtg_engine.models.game import GameState

logger = logging.getLogger(__name__)


def is_monarch(game_state: GameState, player_name: str) -> bool:
    """
    Return True if the given player holds the monarch.

    Used by card effects that reference "if you're the monarch" or similar conditions.
    CR 702.147.
    """
    return game_state.monarch == player_name


def set_monarch(game_state: GameState, player_name: str) -> GameState:
    """
    Set the monarch to the given player.

    Fires a delayed trigger for cards that care about becoming monarch.
    Does nothing if the player is already the monarch.

    Returns a new GameState via model_copy (pure transform).
    """
    if game_state.monarch == player_name:
        return game_state

    old_monarch = game_state.monarch
    logger.info(
        "Monarch: %s becomes the monarch (was %s)", player_name, old_monarch or "none"
    )

    # Fire a delayed "become monarch" trigger for palace jailer / monarch-matters cards
    from mtg_engine.models.game import PendingTrigger
    import uuid
    trigger = PendingTrigger(
        id=str(uuid.uuid4()),
        source_permanent_id="monarch",
        controller=player_name,
        trigger_type="become_monarch",
        effect_description=f"{player_name} becomes the monarch",
        source_card_name="monarch",
    )

    # Pure transform: return new GameState via model_copy
    new_triggers = list(game_state.pending_triggers) + [trigger]
    return game_state.model_copy(update={"monarch": player_name, "pending_triggers": new_triggers})


def handle_end_step_draw(game_state: GameState) -> GameState:
    """
    At the beginning of the end step, if the active player is the monarch,
    they draw a card. CR 702.147.
    """
    if game_state.monarch is None:
        return game_state
    if game_state.active_player != game_state.monarch:
        return game_state

    from mtg_engine.engine.zones import draw_card
    game_state, _ = draw_card(game_state, game_state.active_player)
    logger.info("Monarch draw: %s draws a card", game_state.active_player)
    return game_state


def check_combat_damage_monarch(
    game_state: GameState,
    target_player: str,
    attacker_controller: str,
) -> GameState:
    """
    If a creature deals combat damage to the monarch, the attacker's controller
    becomes the monarch. CR 702.147.
    """
    if game_state.monarch is None:
        return game_state
    if target_player != game_state.monarch:
        return game_state

    return set_monarch(game_state, attacker_controller)
