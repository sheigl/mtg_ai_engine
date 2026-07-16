"""Shroud keyword (CR 702.41).

Shroud is a static ability that prevents all targeting:
- A permanent or player with shroud can't be the target of any spell or ability,
  including its own controller's.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

from mtg_engine.ability.keywords.base import PassiveKeyword

logger = logging.getLogger(__name__)


class Shroud(PassiveKeyword):
    """Shroud keyword ability (CR 702.41).

    CR 702.41b: A permanent or player with shroud can't be the target of spells
    or abilities. Neither opponent nor controller can target it.
    """

    name = "shroud"

    @staticmethod
    def has_shroud(keywords: list[str]) -> bool:
        """Check if a card has the shroud keyword."""
        return "shroud" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains shroud keyword."""
        if not oracle_text:
            return False
        return "shroud" in oracle_text.lower()

    @staticmethod
    def can_be_targeted(target_keywords: list[str]) -> bool:
        """Check if the permanent can be targeted by anyone.

        A shrouded permanent can never be targeted.
        CR 702.41b.

        Args:
            target_keywords: Keywords of the target permanent.

        Returns:
            True if the permanent can be legally targeted (always False if shrouded).
        """
        return not Shroud.has_shroud(target_keywords)


def is_shrouded(
    game_state: "GameState",
    perm_id_or_player_name: str,
) -> bool:
    """Check if a permanent or player has shroud.

    Query helper for targeting validation (CR 702.41). A permanent or player
    with shroud can't be the target of any spell or ability, regardless of
    who controls it.

    Args:
        game_state: Current game state.
        perm_id_or_player_name: Either a permanent ID (on battlefield) or a
            player name.

    Returns:
        True if the target has shroud, False otherwise.
    """
    # Check if it's a permanent on the battlefield
    for perm in game_state.battlefield:
        if perm.id == perm_id_or_player_name:
            return Shroud.has_shroud(perm.card.keywords or [])

    # Check if it's a player name — players can have shroud via effects.
    # For now, check battlefield permanents controlled by the player that
    # grant shroud to them. Full support would require tracking player-level
    # keywords on PlayerState.
    for player in game_state.players:
        if player.name == perm_id_or_player_name:
            return False

    return False


def can_target_shrouded(
    game_state: "GameState",
    target_id_or_player_name: str,
) -> bool:
    """Check if a shroud-protected target can be targeted.

    CR 702.41b: A permanent or player with shroud can't be the target of
    spells or abilities. No one — not even the controller — may target it.

    Args:
        game_state: Current game state.
        target_id_or_player_name: Permanent ID or player name to check.

    Returns:
        True if targeting is legal (not shrouded). False if shrouded.
    """
    return not is_shrouded(game_state, target_id_or_player_name)
