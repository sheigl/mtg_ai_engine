"""Morph keyword ability (CR 702.36).

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

    CR 702.36: "Morph {cost}" means "{cost} rather than pay this creature card's
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

    def get_trigger_description(self) -> str:
        cost_str = self.cost or "{2}{T}"
        return f"Morph {cost_str}: Pay to cast this creature face down as a 2/2"
