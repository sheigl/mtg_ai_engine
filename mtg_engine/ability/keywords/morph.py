"""Morph keyword ability (CR 702.37).

Morph {cost} is an alternative cost that may be paid instead of paying a
creature spell's mana cost. If you pay the morph cost, the creature is cast
face down as a 2/2 colorless creature with no text, no subtype, no rarity,
and no mana cost. You can turn it face up later by paying its mana cost.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_MORPH_PATTERN = re.compile(r"\bMorph\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_MORPH_PLAIN = re.compile(r"\bMorph\b", re.IGNORECASE)


class MorphKeyword(CostKeyword):
    """Morph keyword ability.

    CR 702.37: "Morph {cost}" means "{cost} rather than pay this creature card's
    mana cost to cast it. (You can't reveal a creature with morph unless you're
    casting it from your hand.) Whenever you cast a creature spell with morph, it
    enters the battlefield face down as a 2/2 colorless creature."

    Example: "Morph {2}{T}" — Pay {2}{T} to cast this creature face down.
    """

    name = "morph"

    def __init__(self, cost: str | None = None):
        """Initialize Morph keyword.

        Args:
            cost: The alternative mana cost for morph (e.g., "{2}{T}").
        """
        self.cost = cost

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Morph."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("morph" in k.lower() for k in keywords)
        has_oracle = bool(_MORPH_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_morph(keywords: list[str]) -> bool:
        """Check if a keyword list contains morph."""
        return any("morph" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains morph."""
        if not oracle_text:
            return False
        return bool(_MORPH_PLAIN.search(oracle_text))

    @staticmethod
    def parse_morph_cost(oracle_text: str) -> str | None:
        """Parse the morph cost from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Cost string (e.g., "{2}{T}") or None if not found.
        """
        match = _MORPH_PATTERN.search(oracle_text or "")
        if match:
            return match.group("cost").strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "MorphKeyword | None":
        """Create MorphKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            MorphKeyword if morph is found, None otherwise.
        """
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_morph_cost(oracle_text))
        return None

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply morph (no-op without spell casting context)."""
        return game_state

    def turn_face_up(
        self,
        game_state: "GameState",
        permanent_id: str,
        mana_payment: dict[str, int] | None = None,
    ) -> "GameState":
        """Turn a face-down creature face up by paying its morph cost.

        CR 702.35b: doesn't use the stack, instant speed, can't be countered.
        Pure transform: returns new GameState via model_copy.

        Args:
            game_state: Current game state.
            permanent_id: ID of the face-down permanent to turn face up.
            mana_payment: Optional explicit mana payment dict; if None, auto-deduct
                          from player's mana pool based on morph cost.

        Returns:
            New GameState with the permanent turned face up and mana deducted.
        """
        perm = next((p for p in game_state.battlefield if p.id == permanent_id), None)
        if perm is None:
            logger.warning("Morph turn face up: permanent %s not found", permanent_id)
            return game_state

        if not perm.is_face_down:
            logger.info("Morph turn face up: %s is already face up", perm.card.name)
            return game_state

        # Get morph cost from the card's oracle text
        morph_cost = self.parse_morph_cost(perm.card.oracle_text or "")
        if not morph_cost:
            logger.warning("Morph turn face up: no morph cost found for %s", perm.card.name)
            return game_state

        # Deduct mana from controller's pool
        player_name = perm.controller
        players = list(game_state.players)
        player_idx = next((i for i, p in enumerate(players) if p.name == player_name), None)
        if player_idx is None:
            logger.warning("Morph turn face up: player %s not found", player_name)
            return game_state

        from mtg_engine.engine.mana import can_pay_cost as _can_pay, pay_cost as _pay_cost, parse_mana_cost as _parse_cost

        player = players[player_idx]
        if not _can_pay(player.mana_pool, morph_cost):
            logger.info("Morph turn face up: %s cannot afford %s", player_name, morph_cost)
            return game_state

        # Construct payment dict from pool and cost (pay_cost requires explicit payment)
        cost_dict = _parse_cost(morph_cost)
        payment: dict[str, int] = {}
        for color in ("W", "U", "B", "R", "G"):
            needed = cost_dict.get(color, 0)
            if needed:
                available = getattr(player.mana_pool, color, 0) or 0
                payment[color] = min(needed, available)
        generic_needed = cost_dict.get("generic", 0)
        if generic_needed:
            remaining_generic = sum(getattr(player.mana_pool, c, 0) or 0 for c in ("C", "W", "U", "B", "R", "G"))
            payment["C"] = min(generic_needed, max(0, remaining_generic))

        new_mana_pool = _pay_cost(player.mana_pool, morph_cost, payment)
        players[player_idx] = player.model_copy(update={"mana_pool": new_mana_pool})

        # Turn the permanent face up: clear is_face_down, set power/toughness from real card
        new_perm = perm.model_copy(
            update={
                "is_face_down": False,
                "power_bonus": 0,
                "toughness_bonus": 0,
            }
        )

        # Replace the permanent in battlefield list
        battlefield = [p if p.id != permanent_id else new_perm for p in game_state.battlefield]

        logger.info("Morph: %s turned face up as %s (paid %s)", player_name, perm.card.name, morph_cost)

        return game_state.model_copy(
            update={
                "players": players,
                "battlefield": battlefield,
                "pending_morph_payment": None,  # Clear any pending choice
            }
        )

    def get_trigger_description(self) -> str:
        cost_str = self.cost or "{2}{T}"
        return f"Morph {cost_str}: Pay to cast this creature face down as a 2/2"


# --- Module-level convenience functions ---

def turn_face_up(
    game_state: "GameState",
    permanent_id: str,
    mana_payment: dict[str, int] | None = None,
) -> "GameState":
    """Turn a face-down creature face up by paying its morph cost.

    Convenience wrapper around MorphKeyword.turn_face_up().
    """
    return MorphKeyword().turn_face_up(game_state, permanent_id, mana_payment)


def resolve_with_ai(
    game_state: "GameState",
    permanent_id: str,
) -> "GameState":
    """AI auto-resolves morph face-up: always pays if affordable."""
    return turn_face_up(game_state, permanent_id)
