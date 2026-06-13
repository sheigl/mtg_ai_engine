"""
Day/Night cycle engine (DNG-01).
CR 730: Day/Night Designation.

- Game starts with neither day nor night (is_day = None)
- Day → Night: previous active player cast 0 spells on their turn
- Night → Day: previous active player cast 2+ spells on their turn
- Daybound/Nightbound permanents transform on transition
- Triggers fire on transition for cards like Tovolar's Huntmaster
"""
import logging
from typing import Optional

from mtg_engine.models.game import GameState

logger = logging.getLogger(__name__)


def check_daynight_transition(game_state: GameState) -> GameState:
    """
    Check and apply day/night transition (CR 730.2).
    Called during the UNTAP step as the second part.
    """
    prev_casts = game_state.spells_cast_last_turn

    if game_state.is_day:
        # Day → Night: active player of previous turn cast no spells
        if prev_casts == 0:
            logger.info("Day → Night transition (0 spells cast last turn)")
            game_state.is_day = False
            _transform_daybound_permanents(game_state)
            _add_daynight_trigger(game_state, "day_to_night")
    else:
        # Night → Day: active player of previous turn cast 2+ spells
        if prev_casts >= 2:
            logger.info("Night → Day transition (2+ spells cast last turn)")
            game_state.is_day = True
            _transform_daybound_permanents(game_state)
            _add_daynight_trigger(game_state, "night_to_day")

    return game_state


def _transform_daybound_permanents(game_state: GameState) -> None:
    """
    Transform all permanents with daybound/nightbound (CR 702.145).
    """
    for perm in game_state.battlefield:
        card = perm.card
        # Check if card has daybound or nightbound in its type line or oracle text
        oracle = (card.oracle_text or "").lower()
        type_line = (card.type_line or "").lower()

        has_daybound = "daybound" in oracle or "daybound" in type_line
        has_nightbound = "nightbound" in oracle or "nightbound" in type_line
        if not has_daybound and not has_nightbound:
            continue

        # If the permanent has a back face (DFC), flip it
        if card.faces and len(card.faces) > 1:
            current_face = getattr(perm, "face_index", 0)
            new_face = 1 if current_face == 0 else 0
            perm.face_index = new_face
            logger.info(
                "Day/Night transform: %s face %d → %d",
                card.name, current_face, new_face,
            )


def _add_daynight_trigger(
    game_state: GameState,
    transition_type: str,
) -> None:
    """Add a pending trigger for day/night transition events."""
    from mtg_engine.models.game import PendingTrigger

    trigger = PendingTrigger(
        source_permanent_id="@@daynight_system@@",
        source_card_name="@@daynight_system@@",
        controller="@@system@@",
        trigger_type=f"day_time_changes_{transition_type}",
        effect_description=f"Day/night transition: {transition_type}",
    )
    game_state.pending_triggers.append(trigger)


def set_day(game_state: GameState) -> GameState:
    """Explicitly set the game to day (e.g., when a daybound permanent enters)."""
    if game_state.is_day is not True:
        logger.info("Day explicitly set")
        game_state.is_day = True
        _add_daynight_trigger(game_state, "set_to_day")
    return game_state


def set_night(game_state: GameState) -> GameState:
    """Explicitly set the game to night (e.g., when a nightbound permanent enters)."""
    if game_state.is_day is not False:
        logger.info("Night explicitly set")
        game_state.is_day = False
        _add_daynight_trigger(game_state, "set_to_night")
    return game_state


def is_daytime(game_state: GameState) -> Optional[bool]:
    """Return the current day/night designation: True=day, False=night, None=neither."""
    return game_state.is_day
