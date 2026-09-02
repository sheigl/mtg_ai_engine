"""Deathtouch keyword (CR 702.2).

Deathtouch is a static ability that modifies damage marking:
- Any nonzero amount of damage from a source with deathtouch is considered lethal.
- The damaged creature is destroyed by state-based actions (CR 704.5h).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import PassiveKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)


class Deathtouch(PassiveKeyword):
    """Deathtouch keyword ability (CR 702.2).

    CR 702.2b: Any amount of damage greater than 0 that's dealt to a creature
    by a source with deathtouch is considered to be lethal damage.
    CR 702.2c: The damage marked on that creature is considered to be lethal
    regardless of toughness.
    """

    name = "deathtouch"

    @staticmethod
    def has_deathtouch(keywords: list[str]) -> bool:
        """Check if a card has the deathtouch keyword."""
        return "deathtouch" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains deathtouch keyword."""
        if not oracle_text:
            return False
        return "deathtouch" in oracle_text.lower()

    @staticmethod
    def is_lethal(damage: int, target_toughness: int) -> bool:
        """Check if damage is lethal given deathtouch.

        With deathtouch, any nonzero damage is lethal regardless of toughness.
        CR 702.2c.

        Args:
            damage: Amount of damage dealt by the deathtouch source.
            target_toughness: Toughness of the damaged creature (unused with deathtouch).

        Returns:
            True if the damage is lethal (always true for damage > 0).
        """
        return damage > 0

    @staticmethod
    def min_lethal_damage() -> int:
        """Return minimum damage needed to be lethal with deathtouch.

        With deathtouch, 1 damage is always lethal.
        """
        return 1


def has_deathtouch_perm(game_state: "GameState", perm_id: str) -> bool:
    """Check if a permanent on the battlefield has deathtouch.

    Args:
        game_state: Current game state.
        perm_id: ID of the permanent to check.

    Returns:
        True if the permanent exists on the battlefield and has deathtouch.
    """
    perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if perm is None:
        return False
    return Deathtouch.has_deathtouch(perm.card.keywords or [])


def apply_deathtouch_damage(
    game_state: "GameState",
    source_perm: "Permanent",
    target_perm: "Permanent | None",
    damage_amount: int,
) -> "GameState":
    """Apply deathtouch tracking to a damaged creature via pure transform.

    Sets the __deathtouch_damage__ counter on the target creature so that
    state-based actions (SBA) can destroy it. No-op for planeswalkers,
    non-creatures, or zero/negative damage.

    Args:
        game_state: Current game state.
        source_perm: Source permanent dealing the damage.
        target_perm: Target permanent receiving the damage (may be None).
        damage_amount: Amount of damage being dealt.

    Returns:
        New GameState with __deathtouch_damage__ counter set on target if applicable.
    """
    # No-op for zero/negative damage
    if damage_amount <= 0:
        return game_state

    # No-op if source doesn't have deathtouch
    if not Deathtouch.has_deathtouch(source_perm.card.keywords or []):
        return game_state

    # No-op if no target permanent
    if target_perm is None:
        return game_state

    # No-op for planeswalker targets
    if "planeswalker" in target_perm.card.type_line.lower():
        return game_state

    # Set __deathtouch_damage__ counter on the target creature (pure transform)
    new_counters = dict(target_perm.counters)
    new_counters["__deathtouch_damage__"] = (
        new_counters.get("__deathtouch_damage__", 0) + damage_amount
    )
    new_target = target_perm.model_copy(update={"counters": new_counters})

    game_state = game_state.model_copy(
        update={
            "battlefield": [
                new_target if p.id == target_perm.id else p
                for p in game_state.battlefield
            ]
        }
    )
    logger.debug(
        "Deathtouch: %s dealt %d damage to %s, set __deathtouch_damage__=%d",
        source_perm.card.name,
        damage_amount,
        target_perm.card.name,
        new_counters["__deathtouch_damage__"],
    )
    return game_state


def apply_deathtouch_damage_from_card(
    game_state: "GameState",
    source_keywords: list[str],
    target_id: str,
    damage_amount: int,
) -> "GameState":
    """Apply deathtouch tracking using card keywords (for stack.py where no Permanent is available).

    Looks up the target permanent from the battlefield and applies deathtouch tracking.

    Args:
        game_state: Current game state.
        source_keywords: Keywords list from the source card.
        target_id: ID of the target to damage.
        damage_amount: Amount of damage being dealt.

    Returns:
        New GameState with __deathtouch_damage__ counter set on target if applicable.
    """
    if not Deathtouch.has_deathtouch(source_keywords):
        return game_state

    # Find source permanent for the Permanent parameter (use first matching or dummy)
    source_perm = next(iter(game_state.battlefield), None)
    target_perm = next((p for p in game_state.battlefield if p.id == target_id), None)

    # Create a minimal source perm with the right keywords for apply_deathtouch_damage
    from mtg_engine.models.game import Card, Permanent

    dummy_source = Permanent(
        id="deathtouch-source",
        card=Card(name="Deathtouch Source", type_line="Creature", keywords=source_keywords),
        controller="",
    )
    return apply_deathtouch_damage(game_state, dummy_source, target_perm, damage_amount)
