"""SA-04 Suspend logic (CR 702.61).

Suspend is a keyword ability that can be used to cast a card from outside the
normal casting process. To suspend a card, pay the suspend cost and exile it
with N time counters. At the beginning of your upkeep, remove a time counter.
When the last is removed, cast the spell without paying its mana cost if legal.
If it wouldn't be legal, you can't cast it and it remains exiled.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState

logger = logging.getLogger(__name__)


def parse_suspend(oracle_text: str) -> tuple[int, str] | None:
    """Extract suspend data from oracle text. Returns (N_counters, cost) or None."""
    import re
    match = re.search(r'[Ss]uspend\s+(\d+)[—–-]\s*((?:\{[^}]+\})+)', oracle_text or "")
    if match:
        return int(match.group(1)), match.group(2)
    return None


def has_suspend(card_oracle: str | None) -> bool:
    """Check if card text contains a suspend ability."""
    import re
    return bool(re.search(r'[Ss]uspend\s+\d+[—–-]\s*\{', card_oracle or ""))


def remove_time_counter(game_state: GameState, player_name: str) -> GameState:
    """Remove one time counter from all suspended cards of a player.

    Thin wrapper that delegates to mtg_engine.ability.keywords.suspend.
    Kept for backward compatibility (turn_manager.py and tests import from here).
    """
    from mtg_engine.ability.keywords.suspend import remove_time_counter as _rtc
    return _rtc(game_state, player_name)


def get_suspend_ready_cards(game_state: GameState, player_name: str) -> list[dict]:
    """Get cards that are ready to be cast via suspend (no time counters left).

    Thin wrapper that delegates to mtg_engine.ability.keywords.suspend.
    Kept for backward compatibility (tests import from here).
    """
    from mtg_engine.ability.keywords.suspend import get_ready_cards as _grc
    return _grc(game_state, player_name)
