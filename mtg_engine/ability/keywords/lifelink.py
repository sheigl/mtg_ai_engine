"""Lifelink keyword (CR 702.15).

Lifelink is a static ability that modifies damage events:
- Whenever a source with lifelink deals damage, its controller gains that much life.
- Applies to combat damage and non-combat damage equally.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import PassiveKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)


class Lifelink(PassiveKeyword):
    """Lifelink keyword ability (CR 702.15).

    CR 702.15b: Whenever a source you control with lifelink deals damage,
    you gain that much life.
    """

    name = "lifelink"

    @staticmethod
    def has_lifelink(keywords: list[str]) -> bool:
        """Check if a card has the lifelink keyword."""
        return "lifelink" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains lifelink keyword."""
        if not oracle_text:
            return False
        return "lifelink" in oracle_text.lower()

    @staticmethod
    def apply_lifelink_gain(controller_life: int, damage: int) -> int:
        """Calculate life gain from lifelink.

        Args:
            controller_life: Current life total of the source's controller.
            damage: Amount of damage dealt by the lifelink source.

        Returns:
            New life total after gaining life equal to damage.
        """
        return controller_life + damage


def has_lifelink_perm(game_state: "GameState", perm_id: str) -> bool:
    """Check if a permanent on the battlefield has lifelink.

    Args:
        game_state: Current game state.
        perm_id: ID of the permanent to check.

    Returns:
        True if the permanent exists on the battlefield and has lifelink.
    """
    perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if perm is None:
        return False
    return Lifelink.has_lifelink(perm.card.keywords or [])


def apply_lifelink_to_gamestate(
    game_state: "GameState",
    source_perm: "Permanent",
    damage_amount: int,
) -> "GameState":
    """Apply lifelink life gain to the source's controller via pure transform.

    CR 702.15b: Whenever a source with lifelink deals damage, its controller
    gains that much life. No-op for zero/negative damage.

    Args:
        game_state: Current game state.
        source_perm: Source permanent dealing the damage (must have lifelink).
        damage_amount: Amount of damage being dealt.

    Returns:
        New GameState with controller's life increased by damage amount.
    """
    # No-op for zero/negative damage
    if damage_amount <= 0:
        return game_state

    # No-op if source doesn't have lifelink
    if not Lifelink.has_lifelink(source_perm.card.keywords or []):
        return game_state

    controller_name = source_perm.controller
    new_players = []
    for player in game_state.players:
        if player.name == controller_name:
            old_life = player.life
            new_player = player.model_copy(update={"life": old_life + damage_amount})
            logger.debug(
                "Lifelink: %s gains %d life (now %d) from %s dealing damage",
                controller_name,
                damage_amount,
                new_player.life,
                source_perm.card.name,
            )
            new_players.append(new_player)
        else:
            new_players.append(player)

    return game_state.model_copy(update={"players": new_players})


def apply_lifelink_from_card(
    game_state: "GameState",
    source_keywords: list[str],
    controller_name: str,
    damage_amount: int,
) -> "GameState":
    """Apply lifelink life gain using card keywords (for stack.py where no Permanent is available).

    Args:
        game_state: Current game state.
        source_keywords: Keywords list from the source card.
        controller_name: Name of the player who controls the source.
        damage_amount: Amount of damage being dealt.

    Returns:
        New GameState with controller's life increased by damage amount if applicable.
    """
    if not Lifelink.has_lifelink(source_keywords):
        return game_state

    if damage_amount <= 0:
        return game_state

    new_players = []
    for player in game_state.players:
        if player.name == controller_name:
            old_life = player.life
            new_player = player.model_copy(update={"life": old_life + damage_amount})
            logger.debug(
                "Lifelink (card): %s gains %d life (now %d)",
                controller_name,
                damage_amount,
                new_player.life,
            )
            new_players.append(new_player)
        else:
            new_players.append(player)

    return game_state.model_copy(update={"players": new_players})
