"""SA-04 Morph face-up logic (CR 702.35).

Morph is a static ability that functions while the card with morph is in hand,
any time you could cast a creature spell. The generic mana cost listed in a morph
ability is the morph cost.

Turning a face-down creature face up doesn't use the stack, so it isn't a spell
and can't be countered or responded to. CR 702.35b: You may turn a face-down
creature you control face up any time you have priority by paying its morph cost.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState

logger = logging.getLogger(__name__)


def parse_morph_cost(oracle_text: str) -> str | None:
    """Extract morph cost from oracle text. Returns e.g. '{3}' or None."""
    import re
    match = re.search(r'[Mm]orph\s+((?:\{[^}]+\})+)', oracle_text or "")
    if match:
        return match.group(1)
    return None


def has_morph(card_oracle: str | None) -> bool:
    """Check if card text contains a morph ability."""
    import re
    return bool(re.search(r'[Mm]orph\s+\{', card_oracle or ""))


def apply_morph_turn_face_up(
    game_state: GameState,
    permanent_id: str,
    mana_payment: dict[str, int] | None = None,
) -> GameState:
    """Turn a face-down creature face up by paying its morph cost.

    Thin wrapper that delegates to mtg_engine.ability.keywords.morph.
    Kept for backward compatibility (game.py router and tests import from here).
    """
    from mtg_engine.ability.keywords.morph import turn_face_up as _tfu
    return _tfu(game_state, permanent_id, mana_payment)


def resolve_morph_with_ai(game_state: GameState, permanent_id: str) -> GameState:
    """AI auto-resolves morph face-up: always pays if affordable.

    Thin wrapper that delegates to mtg_engine.ability.keywords.morph.
    Kept for backward compatibility (tests import from here).
    """
    from mtg_engine.ability.keywords.morph import resolve_with_ai as _rwa
    return _rwa(game_state, permanent_id)
