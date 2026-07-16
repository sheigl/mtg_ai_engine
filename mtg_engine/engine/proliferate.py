"""
Proliferate system (PRO-01).
CR 701.27: Choose any number of permanents and/or players that have a counter,
then give each another counter of each kind that permanent or player already has.

All state transforms are pure: functions return new GameState via model_copy(update={...}).
Never mutate perm.counters, player.poison_counters, or game_state fields in place.
"""
import logging

from mtg_engine.models.game import GameState

logger = logging.getLogger(__name__)


def get_proliferate_eligible(game_state: GameState) -> list[dict]:
    """
    Return all permanents and players that have at least one counter.

    Internal engine counters (prefixed with "__") are excluded.

    Each entry: {"id": str, "name": str, "counters": dict, "type": "permanent"|"player"}
    """
    eligible: list[dict] = []

    for perm in game_state.battlefield:
        real_counters = {k: v for k, v in perm.counters.items() if not k.startswith("__")}
        if real_counters:
            eligible.append({
                "id": perm.id,
                "name": perm.card.name,
                "counters": real_counters,
                "type": "permanent",
                "controller": perm.controller,
            })

    for player in game_state.players:
        if player.poison_counters > 0:
            eligible.append({
                "id": player.name,
                "name": player.name,
                "counters": {"poison": player.poison_counters},
                "type": "player",
            })

    return eligible


def apply_proliferate(
    game_state: GameState,
    target_ids: list[str],
) -> GameState:
    """
    Apply proliferate to the given targets. CR 701.27.

    Each target must have at least one counter. For each counter type the
    target already has, one more is added.

    Pure transform: returns new GameState via model_copy(update={...}).
    Never mutates perm.counters or player.poison_counters in place.
    """
    if not target_ids:
        return game_state

    # Build set of target IDs for quick lookup
    target_set = set(target_ids)

    # Separate permanent targets from player targets
    perm_targets = {tid for tid in target_set}
    player_targets: list[str] = []

    new_battlefield = []
    for perm in game_state.battlefield:
        if perm.id in perm_targets and perm.counters:
            # Build new counters dict with incremented values (skip internal)
            new_counters = {}
            for counter_type, count in perm.counters.items():
                if not counter_type.startswith("__"):
                    new_counters[counter_type] = count + 1
                    _emit_counter_event(game_state, perm.id, counter_type, 1)
                else:
                    # Keep internal counters unchanged
                    new_counters[counter_type] = count
            new_battlefield.append(perm.model_copy(update={"counters": new_counters}))
            logger.debug(
                "Proliferate: added counters to permanent %s (%s)",
                perm.card.name, perm.id,
            )
        else:
            new_battlefield.append(perm)

    # Update players list for poison counters
    new_players = []
    for player in game_state.players:
        if player.name in target_set and player.poison_counters > 0:
            _emit_counter_event(game_state, player.name, "poison", 1)
            new_players.append(player.model_copy(
                update={"poison_counters": player.poison_counters + 1}
            ))
            logger.debug("Proliferate: added poison counter to player %s", player.name)
        else:
            new_players.append(player)

    return game_state.model_copy(update={
        "battlefield": new_battlefield,
        "players": new_players,
    })


def _emit_counter_event(
    game_state: GameState,
    target_id: str,
    counter_type: str,
    count: int,
) -> None:
    """Emit a counter-placed event for the proliferated counter."""
    try:
        from mtg_engine.engine.events import EventBus
        bus = EventBus.get_instance()
        from mtg_engine.engine.events import CounterPlacedEvent
        bus.emit(CounterPlacedEvent(
            game_id=game_state.game_id,
            target_id=target_id,
            counter_type=counter_type,
            count=count,
            source_id="proliferate",
        ))
    except Exception:
        pass


def setup_pending_proliferate(game_state: GameState, player_name: str) -> GameState:
    """
    Set the pending_proliferate_choice on the game state so the player can
    select targets via the legal actions system.

    Pure transform: returns new GameState via model_copy(update={...}).
    """
    eligible = get_proliferate_eligible(game_state)
    return game_state.model_copy(update={
        "pending_proliferate_choice": {
            "player": player_name,
            "eligible": eligible,
        },
    })


def _resolve_proliferate_with_ai(
    game_state: GameState,
    controller: str,
) -> GameState:
    """
    Auto-resolve proliferate for an AI player.

    Heuristic: proliferate to all eligible targets controlled by the
    proliferating player (never help opponents). Also includes the
    proliferating player themselves if they have poison counters.

    Pure transform: returns new GameState via model_copy(update={...}).
    """
    eligible = get_proliferate_eligible(game_state)

    # Select only targets controlled by the AI player or the player themselves
    chosen_ids: list[str] = []
    for target in eligible:
        if target["type"] == "permanent":
            controller_match = target.get("controller") == controller
            if controller_match:
                chosen_ids.append(target["id"])
        elif target["type"] == "player":
            # Include the proliferating player themselves (poison counters)
            if target["id"] == controller:
                chosen_ids.append(target["id"])

    logger.info(
        "Proliferate AI: %d targets selected for %s out of %d eligible",
        len(chosen_ids), controller, len(eligible),
    )

    return apply_proliferate(game_state, chosen_ids)
