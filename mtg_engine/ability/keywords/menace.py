"""Menace keyword (CR 702.111).

Menace is a static ability that modifies blocking rules:
- A creature with menace can't be blocked except by two or more creatures
  with flying or reach.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

from mtg_engine.ability.keywords.base import PassiveKeyword

logger = logging.getLogger(__name__)


class Menace(PassiveKeyword):
    """Menace keyword ability (CR 702.111).

    CR 702.111b: An attacking creature with menace can't be blocked unless
    it's blocked by two or more creatures.
    """

    name = "menace"

    @staticmethod
    def has_menace(keywords: list[str]) -> bool:
        """Check if a card has the menace keyword."""
        return "menace" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains menace keyword."""
        if not oracle_text:
            return False
        return "menace" in oracle_text.lower()

    @staticmethod
    def min_blockers() -> int:
        """Return minimum number of blockers required for a creature with menace.

        A creature with menace must be blocked by at least 2 creatures.
        CR 702.111b.
        """
        return 2

    @staticmethod
    def is_block_legal(attacker_keywords: list[str], num_blockers: int) -> bool:
        """Check if a blocking declaration is legal given menace.

        Args:
            attacker_keywords: Keywords of the attacking creature.
            num_blockers: Number of creatures blocking this attacker.

        Returns:
            True if the block is legal (either no menace or 2+ blockers).
        """
        if not Menace.has_menace(attacker_keywords):
            return True
        return num_blockers >= Menace.min_blockers()


def is_menacing(game_state: "GameState", perm_id: str) -> bool:
    """Check if a permanent on the battlefield has menace.

    Query helper for combat blocker assignment (CR 702.111). A creature with
    menace can't be blocked except by two or more creatures with flying or reach.

    Args:
        game_state: Current game state.
        perm_id: Permanent ID on the battlefield.

    Returns:
        True if the permanent has menace, False otherwise (including if the
        permanent is not found).
    """
    for perm in game_state.battlefield:
        if perm.id == perm_id:
            return Menace.has_menace(perm.card.keywords or [])

    logger.debug("Permanent %s not found on battlefield for menace check", perm_id)
    return False


def can_block_menacing(
    game_state: "GameState",
    attacker_perm_id: str,
    blocker_perm_ids: list[str],
) -> bool:
    """Check if the given blockers legally block a menacing attacker.

    CR 702.111b: An attacking creature with menace can't be blocked unless
    it's blocked by two or more creatures.

    Args:
        game_state: Current game state.
        attacker_perm_id: Permanent ID of the attacking creature.
        blocker_perm_ids: List of permanent IDs attempting to block.

    Returns:
        True if the block is legal (attacker has no menace, or 2+ blockers).
        False if the attacker has menace and fewer than 2 creatures are blocking.
    """
    if not is_menacing(game_state, attacker_perm_id):
        return True  # No menace, any number of blockers is fine

    return len(blocker_perm_ids) >= Menace.min_blockers()
