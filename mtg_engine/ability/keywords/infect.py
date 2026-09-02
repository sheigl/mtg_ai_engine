"""Infect, Wither, and Poisonous keywords (CR 702.90, 702.129, 702.118).

Infect modifies damage: creatures get -1/-1 counters, players get poison counters.
Wither is similar but only affects creatures (-1/-1 counters, normal player damage).
Poisonous N gives a player N poison counters on combat damage.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from pydantic import BaseModel
from mtg_engine.ability.keywords.base import PassiveKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)


class Infect(PassiveKeyword):
    """Infect keyword (CR 702.90).

    Infect is a static ability that modifies how damage is dealt:
    - Damage to creatures causes -1/-1 counters instead of marked damage
    - Damage to players causes poison counters instead of life loss
    - Damage to planeswalkers reduces loyalty normally (infect doesn't affect this)
    """

    name = "infect"

    @staticmethod
    def has_infect(keywords: list[str]) -> bool:
        """Check if a card has the infect keyword."""
        return "infect" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains infect keyword."""
        if not oracle_text:
            return False
        return "infect" in oracle_text.lower()


class Wither(PassiveKeyword):
    """Wither keyword (CR 702.129).

    Wither is similar to infect but only applies to creatures:
    - Damage to creatures causes -1/-1 counters instead of marked damage
    - Damage to players is normal (life loss, not poison)
    - Damage to planeswalkers reduces loyalty normally
    """

    name = "wither"

    @staticmethod
    def has_wither(keywords: list[str]) -> bool:
        """Check if a card has the wither keyword."""
        return "wither" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains wither keyword."""
        if not oracle_text:
            return False
        return "wither" in oracle_text.lower()


class PoisonousKeyword(BaseModel):
    """Poisonous keyword (CR 702.118).

    Poisonous N — Whenever this creature deals combat damage to a player,
    that player gets N poison counters.
    """

    name: str = "poisonous"
    poison_amount: int = 0

    @staticmethod
    def from_oracle_text(oracle_text: str) -> PoisonousKeyword | None:
        """Parse poisonous N from oracle text."""
        if not oracle_text:
            return None
        m = re.search(r"poisonous\s+(\d+)", oracle_text.lower())
        if m:
            return PoisonousKeyword(poison_amount=int(m.group(1)))
        return None

    def apply(self, game_state: "GameState", source_id: str, target_player_name: str) -> "GameState":
        """Apply poisonous effect - add poison counters to player (pure transform)."""
        new_players = []
        for player in game_state.players:
            if player.name == target_player_name:
                new_count = player.poison_counters + self.poison_amount
                updates: dict = {"poison_counters": new_count}
                if new_count >= 10:
                    updates["has_lost"] = True
                new_players.append(player.model_copy(update=updates))
            else:
                new_players.append(player)

        logger.debug(
            "Poisonous %d: %s got %d poison counters (now %d)",
            self.poison_amount,
            target_player_name,
            self.poison_amount,
            next(p for p in new_players if p.name == target_player_name).poison_counters,
        )
        return game_state.model_copy(update={"players": new_players})


# Legacy aliases for backward compatibility
InfectKeyword = Infect
WitherKeyword = Wither


def has_infect_perm(game_state: "GameState", perm_id: str) -> bool:
    """Check if a permanent on the battlefield has infect.

    Args:
        game_state: Current game state.
        perm_id: ID of the permanent to check.

    Returns:
        True if the permanent exists on the battlefield and has infect.
    """
    perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if perm is None:
        return False
    return Infect.has_infect(perm.card.keywords or [])


def apply_infect_damage_to_creature(
    game_state: "GameState",
    target_perm: "Permanent",
    damage_amount: int,
) -> "GameState":
    """Apply infect/wither damage to a creature as -1/-1 counters (pure transform).

    CR 702.90b / CR 702.129b: Damage from an infect/wither source is dealt to
    creatures in the form of -1/-1 counters instead of being marked.

    Args:
        game_state: Current game state.
        target_perm: Target creature receiving the damage.
        damage_amount: Amount of damage (becomes N -1/-1 counters).

    Returns:
        New GameState with -1/-1 counters added to the target creature.
    """
    if damage_amount <= 0:
        return game_state

    # Add -1/-1 counters
    new_counters = dict(target_perm.counters)
    current_minus1 = new_counters.get("-1/-1", 0)
    new_counters["-1/-1"] = current_minus1 + damage_amount
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
        "Infect: %s got %d -1/-1 counters (now %d)",
        target_perm.card.name,
        damage_amount,
        new_counters["-1/-1"],
    )
    return game_state


def apply_infect_poison_to_player(
    game_state: "GameState",
    target_player_name: str,
    poison_count: int,
) -> "GameState":
    """Apply infect damage to a player as poison counters (pure transform).

    CR 702.90c: Damage dealt to a player by a source with infect causes that
    player to get that many poison counters instead of losing that much life.

    Args:
        game_state: Current game state.
        target_player_name: Name of the player receiving poison counters.
        poison_count: Number of poison counters (equals damage amount).

    Returns:
        New GameState with poison counters added to the target player.
    """
    if poison_count <= 0:
        return game_state

    new_players = []
    for player in game_state.players:
        if player.name == target_player_name:
            new_count = player.poison_counters + poison_count
            updates: dict = {"poison_counters": new_count}
            if new_count >= 10:
                updates["has_lost"] = True
            new_players.append(player.model_copy(update=updates))
        else:
            new_players.append(player)

    logger.debug(
        "Infect poison: %s got %d poison counters (now %d)",
        target_player_name,
        poison_count,
        next((p.poison_counters for p in new_players if p.name == target_player_name), 0),
    )
    return game_state.model_copy(update={"players": new_players})


def apply_infect_damage(
    game_state: "GameState",
    source_perm: "Permanent",
    target_perm: "Permanent | None",
    target_player_name: str | None,
    damage_amount: int,
) -> "GameState":
    """Apply full infect damage logic based on target type (pure transform).

    Routes to the correct handler: -1/-1 counters for creatures, poison for players.
    No-op for planeswalkers (normal loyalty reduction applies elsewhere).

    Args:
        game_state: Current game state.
        source_perm: Source permanent dealing the damage (must have infect/wither).
        target_perm: Target permanent (creature or planeswalker), may be None.
        target_player_name: Target player name, may be None if targeting a permanent.
        damage_amount: Amount of damage being dealt.

    Returns:
        New GameState with appropriate counters applied.
    """
    has_infect = Infect.has_infect(source_perm.card.keywords or [])
    has_wither = Wither.has_wither(source_perm.card.keywords or [])

    if not (has_infect or has_wither):
        return game_state

    if damage_amount <= 0:
        return game_state

    # Creature target: -1/-1 counters (both infect and wither)
    if target_perm is not None:
        type_lower = target_perm.card.type_line.lower()
        if "creature" in type_lower:
            return apply_infect_damage_to_creature(game_state, target_perm, damage_amount)
        # Planeswalker: no special handling (normal loyalty reduction elsewhere)

    # Player target: poison counters (infect only, not wither)
    if has_infect and target_player_name:
        return apply_infect_poison_to_player(game_state, target_player_name, damage_amount)

    return game_state


def apply_infect_from_card(
    game_state: "GameState",
    source_keywords: list[str],
    controller_name: str,
    target_perm_id: str | None,
    target_player_name: str | None,
    damage_amount: int,
) -> "GameState":
    """Apply infect/wither damage using card keywords (for stack.py where no Permanent is available).

    Args:
        game_state: Current game state.
        source_keywords: Keywords list from the source card.
        controller_name: Name of the player who controls the source.
        target_perm_id: ID of target permanent, may be None.
        target_player_name: Target player name, may be None.
        damage_amount: Amount of damage being dealt.

    Returns:
        New GameState with appropriate counters applied.
    """
    has_infect = Infect.has_infect(source_keywords)
    has_wither = Wither.has_wither(source_keywords)

    if not (has_infect or has_wither):
        return game_state

    # For creature target, look up from battlefield
    if target_perm_id:
        target_perm = next((p for p in game_state.battlefield if p.id == target_perm_id), None)
        if target_perm and "creature" in target_perm.card.type_line.lower():
            return apply_infect_damage_to_creature(game_state, target_perm, damage_amount)

    # For player target (infect only)
    if has_infect and target_player_name:
        return apply_infect_poison_to_player(game_state, target_player_name, damage_amount)

    return game_state
