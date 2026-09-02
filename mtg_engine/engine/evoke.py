"""SA-04 Evoke logic (CR 702.41).

Evoke is a keyword ability that appears as an additional mana cost on certain
creatures. When a creature with evoke enters the battlefield, its controller
must sacrifice it at the beginning of the next end step. This is mandatory,
not optional.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState

logger = logging.getLogger(__name__)


def parse_evoke_cost(oracle_text: str) -> str | None:
    """Extract evoke cost from oracle text. Returns e.g. '{2}' or None."""
    import re
    match = re.search(r'[Ee]voke\s+((?:\{[^}]+\})+)', oracle_text or "")
    if match:
        return match.group(1)
    return None


def has_evoke(card_oracle: str | None) -> bool:
    """Check if card text contains an evoke ability."""
    import re
    return bool(re.search(r'[Ee]voke\s+\{', card_oracle or ""))


def queue_evoke_sacrifice(
    game_state: GameState,
    permanent_id: str,
    player_name: str,
    card_name: str,
) -> GameState:
    """Queue a mandatory evoke sacrifice for the end step.

    Thin wrapper that delegates to mtg_engine.ability.keywords.evoke.
    Kept for backward compatibility (stack.py and tests import from here).
    """
    from mtg_engine.ability.keywords.evoke import queue_sacrifice as _qs
    return _qs(game_state, permanent_id, player_name, card_name)


def resolve_evoke_sacrifice(game_state: GameState) -> GameState:
    """Execute the mandatory evoke sacrifice.

    Thin wrapper that delegates to mtg_engine.ability.keywords.evoke.
    Kept for backward compatibility (turn_manager.py and tests import from here).
    """
    from mtg_engine.ability.keywords.evoke import resolve_sacrifice as _rs
    return _rs(game_state)


def resolve_evoke_with_ai(game_state: GameState) -> GameState:
    """AI auto-resolves evoke sacrifice (always sacrifices as mandatory).

    Thin wrapper that delegates to mtg_engine.ability.keywords.evoke.
    Kept for backward compatibility (tests import from here).
    """
    from mtg_engine.ability.keywords.evoke import resolve_with_ai as _rwa
    return _rwa(game_state)
