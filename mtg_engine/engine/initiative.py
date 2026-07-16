"""
Initiative mechanic (INT-01).
CR 702.148: The Initiative.

- When a creature deals combat damage to the initiative holder, the attacker gains it.
- At the beginning of the initiative holder's upkeep, they venture into Undercity.
- Undercity is a 5-room dungeon defined in models/dungeon.py.

All state transforms are pure: functions return new GameState via model_copy.
"""
import logging
import uuid

from mtg_engine.models.game import GameState, PendingTrigger

logger = logging.getLogger(__name__)


def set_initiative(game_state: GameState, player_name: str) -> GameState:
    """
    Set the initiative to the given player. Returns new GameState.
    Fires a trigger for cards that care about gaining initiative.
    """
    if game_state.initiative == player_name:
        return game_state

    old = game_state.initiative
    logger.info(
        "Initiative: %s gains the initiative (was %s)",
        player_name, old or "none",
    )

    trigger = PendingTrigger(
        id=str(uuid.uuid4()),
        source_permanent_id="initiative",
        source_card_name="initiative",
        controller=player_name,
        trigger_type="gain_initiative",
        effect_description=f"{player_name} gains the initiative",
    )

    return game_state.model_copy(update={
        "initiative": player_name,
        "pending_triggers": [*game_state.pending_triggers, trigger],
    })


def handle_upkeep_venture(game_state: GameState) -> GameState:
    """
    At the beginning of the initiative holder's upkeep, they venture into the
    Undercity dungeon. CR 702.148.
    """
    if game_state.initiative is None:
        return game_state
    if game_state.active_player != game_state.initiative:
        return game_state

    from mtg_engine.engine.dungeon import venture
    game_state = venture(game_state, game_state.active_player, dungeon_name="Undercity")
    logger.info("Initiative venture: %s ventures into Undercity", game_state.active_player)
    return game_state


def check_combat_damage_initiative(
    game_state: GameState,
    target_player: str,
    attacker_controller: str,
) -> GameState:
    """
    If a creature deals combat damage to the initiative holder, the attacker's
    controller gains the initiative. CR 702.148.
    """
    if game_state.initiative is None:
        return game_state
    if target_player != game_state.initiative:
        return game_state

    return set_initiative(game_state, attacker_controller)
