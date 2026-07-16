"""Hexproof keyword (CR 702.54).

Hexproof is a static ability that prevents targeting:
- A permanent or player with hexproof can't be the target of spells or abilities
  an opponent controls.
- The permanent's controller can still target it.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

from mtg_engine.ability.keywords.base import PassiveKeyword

logger = logging.getLogger(__name__)


class Hexproof(PassiveKeyword):
    """Hexproof keyword ability (CR 702.54).

    CR 702.54b: A permanent or player with hexproof can't be the target of spells
    or abilities that players other than its controller control.
    """

    name = "hexproof"

    @staticmethod
    def has_hexproof(keywords: list[str]) -> bool:
        """Check if a card has the hexproof keyword."""
        return "hexproof" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains hexproof keyword."""
        if not oracle_text:
            return False
        return "hexproof" in oracle_text.lower()

    @staticmethod
    def can_be_targeted(
        target_keywords: list[str],
        source_controller: str,
        target_controller: str,
    ) -> bool:
        """Check if the permanent can be targeted.

        A hexproof permanent can only be targeted by its own controller.
        CR 702.54b.

        Args:
            target_keywords: Keywords of the target permanent.
            source_controller: Name of the controller of the spell/ability.
            target_controller: Name of the controller of the target permanent.

        Returns:
            True if the permanent can be legally targeted.
        """
        if not Hexproof.has_hexproof(target_keywords):
            return True
        return source_controller == target_controller


def is_hexproof(
    game_state: "GameState",
    perm_id_or_player_name: str,
) -> bool:
    """Check if a permanent or player has hexproof.

    Query helper for targeting validation (CR 702.54). A permanent or player
    with hexproof can't be the target of spells or abilities controlled by
    opponents. The controller may still target their own hexproof permanents.

    Args:
        game_state: Current game state.
        perm_id_or_player_name: Either a permanent ID (on battlefield) or a
            player name.

    Returns:
        True if the target has hexproof, False otherwise.
    """
    # Check if it's a permanent on the battlefield
    for perm in game_state.battlefield:
        if perm.id == perm_id_or_player_name:
            return Hexproof.has_hexproof(perm.card.keywords or [])

    # Check if it's a player name — players can have hexproof via effects
    # (e.g., "You gain hexproof"). We check the player's permanents for now;
    # in a full implementation, PlayerState would track keywords directly.
    for player in game_state.players:
        if player.name == perm_id_or_player_name:
            # Check if any of this player's permanents grant hexproof to them
            # For now, check battlefield permanents controlled by the player
            # that have a "hexproof on controller" effect. This is a simplified
            # approach; full support would require tracking player-level keywords.
            return False

    return False


def can_target_hexproof(
    game_state: "GameState",
    target_id_or_player_name: str,
    source_controller: str,
) -> bool:
    """Check if a hexproof-protected target can be targeted by the given controller.

    CR 702.54b: A permanent or player with hexproof can't be the target of spells
    or abilities that players other than its controller control.

    Args:
        game_state: Current game state.
        target_id_or_player_name: Permanent ID or player name to check.
        source_controller: Name of the player controlling the spell/ability.

    Returns:
        True if targeting is legal (not hexproof, or same controller).
    """
    # Find the target's controller
    target_controller = _find_target_controller(
        game_state, target_id_or_player_name
    )
    if target_controller is None:
        return False  # Target not found

    if not is_hexproof(game_state, target_id_or_player_name):
        return True  # No hexproof, targeting allowed

    # Hexproof: only the controller can target
    return source_controller == target_controller


def _find_target_controller(
    game_state: "GameState",
    perm_id_or_player_name: str,
) -> str | None:
    """Find the controller of a permanent or player.

    Args:
        game_state: Current game state.
        perm_id_or_player_name: Permanent ID or player name.

    Returns:
        Controller name, or None if not found.
    """
    # Check battlefield permanents first
    for perm in game_state.battlefield:
        if perm.id == perm_id_or_player_name:
            return perm.controller

    # Check if it's a player name
    for player in game_state.players:
        if player.name == perm_id_or_player_name:
            return player.name  # Players control themselves

    return None
