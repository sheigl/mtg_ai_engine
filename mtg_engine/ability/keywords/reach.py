"""Reach keyword (CR 702.17).

Reach is a static ability that modifies blocking rules:
- A creature with reach can block creatures with flying.
- Without reach, only creatures with flying can block other flying creatures.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

from mtg_engine.ability.keywords.base import PassiveKeyword

logger = logging.getLogger(__name__)


class Reach(PassiveKeyword):
    """Reach keyword ability (CR 702.17).

    CR 702.17b: Creatures with flying or reach can block creatures with flying,
    ignoring the normal restriction that only flying creatures can block flying creatures.
    """

    name = "reach"

    @staticmethod
    def has_reach(keywords: list[str]) -> bool:
        """Check if a card has the reach keyword."""
        return "reach" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains reach keyword."""
        if not oracle_text:
            return False
        return "reach" in oracle_text.lower()

    @staticmethod
    def can_block_flying(blocker_keywords: list[str]) -> bool:
        """Check if a blocker can block a flying creature.

        A creature can block flying if it has flying or reach.
        CR 702.9b, CR 702.17b.

        Args:
            blocker_keywords: Keywords of the blocking creature.

        Returns:
            True if the blocker can block a flying creature.
        """
        kw_lower = [k.lower() for k in blocker_keywords]
        return "flying" in kw_lower or "reach" in kw_lower


def has_reach(game_state: GameState, perm_id: str) -> bool:
    """Check if a permanent on the battlefield has reach.

    Query helper for combat blocker assignment (CR 702.17). A creature with
    reach can block creatures with flying, ignoring the normal restriction
    that only flying creatures can block flying creatures.

    Args:
        game_state: Current game state.
        perm_id: Permanent ID on the battlefield.

    Returns:
        True if the permanent has reach, False otherwise (including if the
        permanent is not found).
    """
    for perm in game_state.battlefield:
        if perm.id == perm_id:
            return Reach.has_reach(perm.card.keywords or [])

    logger.debug("Permanent %s not found on battlefield for reach check", perm_id)
    return False


def can_block_flying(game_state: GameState, blocker_perm_id: str) -> bool:
    """Check if a permanent can block flying creatures.

    CR 702.9b / CR 702.17b: A creature can block flying only if it has
    flying or reach. This helper checks the battlefield for the blocker and
    returns whether it satisfies that requirement.

    Args:
        game_state: Current game state.
        blocker_perm_id: Permanent ID of the potential blocker on the battlefield.

    Returns:
        True if the blocker has flying or reach (can block flying creatures).
        False if neither keyword is present, or if the permanent is not found.
    """
    for perm in game_state.battlefield:
        if perm.id == blocker_perm_id:
            return Reach.can_block_flying(perm.card.keywords or [])

    logger.debug("Permanent %s not found on battlefield for can_block_flying check", blocker_perm_id)
    return False
