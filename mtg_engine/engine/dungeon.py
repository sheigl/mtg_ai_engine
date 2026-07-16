"""
Dungeon / Venture engine (VEN-01).
CR 701.61: Venture into the dungeon.

When a player ventures, they:
1. If they don't have a dungeon in progress, choose a dungeon to start.
2. Advance to the next room (room 0 → room 1, etc.).
3. The ability of the room they just entered goes on the stack.
4. If they complete the final room, the dungeon is completed and they may
   start a new one on a future venture.

All state transforms are pure: functions return new GameState via model_copy.
"""
import logging
import uuid
from typing import Optional

from mtg_engine.models.game import GameState, PendingTrigger
from mtg_engine.models.dungeon import (
    DUNGEON_MAP, ALL_DUNGEONS, DungeonProgress, DungeonRoomChoice,
)

logger = logging.getLogger(__name__)


def get_dungeon_progress(
    game_state: GameState,
    player_name: str,
) -> Optional[DungeonProgress]:
    """Return the current dungeon progress for a player, or None."""
    return game_state.player_dungeons.get(player_name)


def set_dungeon_progress(
    game_state: GameState,
    player_name: str,
    progress: DungeonProgress,
) -> GameState:
    """Set the dungeon progress for a player (pure transform)."""
    new_dungeons = dict(game_state.player_dungeons)
    new_dungeons[player_name] = progress
    return game_state.model_copy(update={"player_dungeons": new_dungeons})


def start_dungeon(
    game_state: GameState,
    player_name: str,
    dungeon_name: str,
) -> tuple[GameState, str]:
    """
    Start a new dungeon for a player.

    Returns (game_state, room_ability_text).
    """
    if dungeon_name not in DUNGEON_MAP:
        msg = f"Unknown dungeon: {dungeon_name}"
        raise ValueError(msg)

    progress = DungeonProgress(dungeon_name=dungeon_name)
    game_state = set_dungeon_progress(game_state, player_name, progress)
    room_text = progress.current_room.ability if progress.current_room else ""
    logger.info("Venture: %s starts dungeon %s; room 0: %s",
                player_name, dungeon_name, room_text)
    return game_state, room_text


def _apply_room_effect(
    game_state: GameState,
    player_name: str,
    ability_text: str,
) -> GameState:
    """
    Route a room's ability text through stack resolution.

    Uses _apply_single_effect_text so existing patterns (draw, scry, gain life,
    venture into the dungeon, etc.) work without hard-coding each room's logic.
    """
    from mtg_engine.engine.stack import _apply_single_effect_text
    from mtg_engine.models.game import Card, StackObject

    stack_obj = StackObject(
        source_card=Card(name="Dungeon Room", oracle_text=ability_text),
        controller=player_name,
    )
    return _apply_single_effect_text(game_state, stack_obj, ability_text)


def venture(
    game_state: GameState,
    player_name: str,
    dungeon_name: Optional[str] = None,
) -> GameState:
    """
    The player ventures into the dungeon.

    - If no dungeon in progress, they choose one (default: first available).
    - Advance to the next room.
    - If the dungeon is now complete, increment completed count.
    - The room ability fires via stack resolution.
    - If the room has choices for a human player, queue pending_dungeon_room_choice.

    Returns updated game state (pure transform).
    """
    progress = get_dungeon_progress(game_state, player_name)

    if progress is None or progress.is_complete:
        # Use provided dungeon name, or default to first available
        chosen = dungeon_name or ALL_DUNGEONS[0].name
        progress = DungeonProgress(dungeon_name=chosen)
        logger.info("Venture: %s starts new dungeon: %s", player_name, chosen)

    # Advance room
    progress = progress.advance()
    game_state = set_dungeon_progress(game_state, player_name, progress)

    # Check if dungeon is now complete (pure transform)
    if progress.is_complete:
        current_count = game_state.player_completed_dungeons.get(player_name, 0)
        new_counts = dict(game_state.player_completed_dungeons)
        new_counts[player_name] = current_count + 1
        game_state = game_state.model_copy(update={"player_completed_dungeons": new_counts})
        logger.info("Venture: %s completed dungeon %s (total: %d)",
                    player_name, progress.dungeon_name,
                    new_counts[player_name])
    else:
        # Room ability text can be used for trigger description
        room = progress.current_room
        if room:
            logger.info("Venture: %s enters room %d: %s — %s",
                        player_name, room.index, room.name, room.ability)

            # Check if room has choices
            if room.choices:
                # For human players, queue the choice; for AI, auto-resolve
                is_human = game_state.human_player_name == player_name
                if is_human:
                    new_pending_choice = {
                        "player": player_name,
                        "dungeon_name": progress.dungeon_name,
                        "room_index": room.index,
                        "choices": [c.model_dump() for c in room.choices],
                    }
                    game_state = game_state.model_copy(
                        update={"pending_dungeon_room_choice": new_pending_choice}
                    )
                    logger.info("Venture: queued room choice for %s", player_name)
                else:
                    # AI: pick default or first choice
                    chosen = next((c for c in room.choices if c.is_default), room.choices[0])
                    game_state = _apply_room_effect(
                        game_state, player_name, chosen.outcome_ability
                    )
                    logger.info("Venture: AI chose %s for %s", chosen.choice_id, player_name)
                return game_state

            # No choices — fire room ability via stack resolution
            game_state = _apply_room_effect(game_state, player_name, room.ability)

    return game_state


def get_available_dungeons() -> list[str]:
    """Return the list of available dungeon names."""
    return list(DUNGEON_MAP.keys())


def get_room_count(player_name: str, game_state: GameState) -> int:
    """Return the number of rooms completed by a player in their current dungeon."""
    progress = get_dungeon_progress(game_state, player_name)
    if progress is None:
        return 0
    return progress.current_room_index


def get_completed_dungeon_count(player_name: str, game_state: GameState) -> int:
    """Return the number of dungeons the player has completed."""
    return game_state.player_completed_dungeons.get(player_name, 0)
