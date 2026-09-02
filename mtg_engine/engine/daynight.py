"""
Day/Night cycle engine (DNG-01).
CR 730: Day/Night Designation.

- Game starts with neither day nor night (is_day = None)
- Day → Night: previous active player cast 0 spells on their turn
- Night → Day: previous active player cast 2+ spells on their turn
- Daybound/Nightbound permanents transform on transition
- Triggers fire on transition for cards like Tovolar's Huntmaster

All functions return new GameState via model_copy — no direct mutations.
"""
import logging
from typing import Optional

from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)


def check_daynight_transition(game_state: GameState) -> GameState:
    """Check and apply day/night transition (CR 730.2). Returns new GameState."""
    prev_casts = game_state.spells_cast_last_turn

    if game_state.is_day is None:
        return game_state  # No transition possible when neither day nor night

    if game_state.is_day:
        # Day → Night: active player of previous turn cast no spells
        if prev_casts == 0:
            logger.info("Day → Night transition (0 spells cast last turn)")
            new_battlefield, transformed_ids = _transform_daybound_permanents(game_state)
            gs = game_state.model_copy(update={
                "is_day": False,
                "battlefield": new_battlefield,
            })
            # Wire: Transformed Trigger (CR 711.3)
            from mtg_engine.engine.triggers import check_transformed_triggers as _check_transformed
            gs = _check_transformed(gs, transformed_ids)
            return gs
    else:
        # Night → Day: active player of previous turn cast 2+ spells
        if prev_casts >= 2:
            logger.info("Night → Day transition (2+ spells cast last turn)")
            new_battlefield, transformed_ids = _transform_daybound_permanents(game_state)
            gs = game_state.model_copy(update={
                "is_day": True,
                "battlefield": new_battlefield,
            })
            # Wire: Transformed Trigger (CR 711.3)
            from mtg_engine.engine.triggers import check_transformed_triggers as _check_transformed
            gs = _check_transformed(gs, transformed_ids)
            return gs

    return game_state  # No transition — return original (same object is fine)


def _transform_daybound_permanents(game_state: GameState) -> tuple[list[Permanent], list[str]]:
    """Transform all daybound/nightbound permanents. Returns (NEW battlefield list, transformed perm IDs)."""
    new_battlefield = []
    transformed_ids = []
    for perm in game_state.battlefield:
        card = perm.card
        oracle = (card.oracle_text or "").lower()
        type_line = (card.type_line or "").lower()

        has_daybound = "daybound" in oracle or "daybound" in type_line
        has_nightbound = "nightbound" in oracle or "nightbound" in type_line

        if not has_daybound and not has_nightbound:
            new_battlefield.append(perm)
            continue

        # DFC with back face — flip it
        if card.faces and len(card.faces) > 1:
            current_face = getattr(perm, "face_index", 0)
            new_face = 1 if current_face == 0 else 0
            new_perm = perm.model_copy(update={"face_index": new_face})
            logger.info("Day/Night transform: %s face %d → %d", card.name, current_face, new_face)
            new_battlefield.append(new_perm)
            transformed_ids.append(perm.id)
        else:
            # Has keyword but no faces — keep as-is (shouldn't happen in practice)
            new_battlefield.append(perm)

    return new_battlefield, transformed_ids


def set_day(game_state: GameState) -> GameState:
    """Explicitly set the game to day. Returns new GameState if changed."""
    if game_state.is_day is not True:
        logger.info("Day explicitly set")
        return game_state.model_copy(update={"is_day": True})
    return game_state


def set_night(game_state: GameState) -> GameState:
    """Explicitly set the game to night. Returns new GameState if changed."""
    if game_state.is_day is not False:
        logger.info("Night explicitly set")
        return game_state.model_copy(update={"is_day": False})
    return game_state


def is_daytime(game_state: GameState) -> Optional[bool]:
    """Return the current day/night designation: True=day, False=night, None=neither."""
    return game_state.is_day
