"""
Proliferate system (PRO-01).
CR 701.27: Choose any number of permanents and/or players that have a counter,
then give each another counter of each kind that permanent or player already has.
"""
import logging

from mtg_engine.models.game import GameState

logger = logging.getLogger(__name__)


def get_proliferate_eligible(game_state: GameState) -> list[dict]:
    """
    Return all permanents and players that have at least one counter.

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
    Apply proliferate to the given targets.

    Each target must have at least one counter. For each counter type the
    target already has, one more is added.
    """
    for target_id in target_ids:
        # Try permanent
        perm = next((p for p in game_state.battlefield if p.id == target_id), None)
        if perm:
            for counter_type, count in list(perm.counters.items()):
                if not counter_type.startswith("__"):
                    perm.counters[counter_type] = count + 1
                    _emit_counter_event(game_state, target_id, counter_type, 1)
            logger.debug(
                "Proliferate: added counters to permanent %s (%s)",
                perm.card.name, target_id,
            )
            continue

        # Try player
        target_player = next((p for p in game_state.players if p.name == target_id), None)
        if target_player and target_player.poison_counters > 0:
            target_player.poison_counters += 1
            _emit_counter_event(game_state, target_id, "poison", 1)
            logger.debug("Proliferate: added poison counter to player %s", target_id)

    return game_state


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
    """
    eligible = get_proliferate_eligible(game_state)
    game_state.pending_proliferate_choice = {
        "player": player_name,
        "eligible": eligible,
    }
    return game_state
