"""
Dungeon / Venture engine (VEN-01).
CR 701.61: Venture into the dungeon.

When a player ventures, they:
1. If they don't have a dungeon in progress, choose a dungeon to start.
2. Advance to the next room (room 0 → room 1, etc.).
3. The ability of the room they just entered goes on the stack.
4. If they complete the final room, the dungeon is completed and they may
   start a new one on a future venture.
"""
import logging
from typing import Optional

from mtg_engine.models.game import GameState
from mtg_engine.models.dungeon import (
    DUNGEON_MAP, ALL_DUNGEONS, DungeonProgress,
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
    """Set the dungeon progress for a player."""
    game_state.player_dungeons[player_name] = progress
    return game_state


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


def venture(game_state: GameState, player_name: str, dungeon_name: Optional[str] = None) -> GameState:
    """
    The player ventures into the dungeon.

    - If no dungeon in progress, they choose one (default: first available).
    - Advance to the next room.
    - If the dungeon is now complete, increment completed count.
    - The room ability fires.

    Returns updated game state.
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

    # Check if dungeon is now complete
    if progress.is_complete:
        game_state.player_completed_dungeons[player_name] = (
            game_state.player_completed_dungeons.get(player_name, 0) + 1
        )
        logger.info("Venture: %s completed dungeon %s (total: %d)",
                    player_name, progress.dungeon_name,
                    game_state.player_completed_dungeons[player_name])
    else:
        # Room ability text can be used for trigger description
        room = progress.current_room
        if room:
            logger.info("Venture: %s enters room %d: %s — %s",
                        player_name, room.index, room.name, room.ability)

            # Add a pending trigger for the room ability
            from mtg_engine.models.game import PendingTrigger
            import uuid
            trigger = PendingTrigger(
                id=str(uuid.uuid4()),
                source_permanent_id="dungeon",
                controller=player_name,
                trigger_type="dungeon_room",
                effect_description=f"{progress.dungeon_name} — Room {room.index}: {room.ability}",
                source_card_name=progress.dungeon_name,
            )
            game_state.pending_triggers.append(trigger)

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
