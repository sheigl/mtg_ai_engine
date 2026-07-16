"""Entwine keyword ability (CR 702.39).

Entwine {cost} is an additional cost that may be paid as a multimode spell
is cast. If you pay the entwine cost, you choose all modes of the spell.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_ENTWINE_PATTERN = re.compile(r"\bEntwine\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_ENTWINE_PLAIN = re.compile(r"\bEntwine\b", re.IGNORECASE)


class EntwineKeyword(CostKeyword):
    """Entwine keyword ability.

    CR 702.39: "Entwine {cost}" is an additional cost that may be paid as a
    multimode spell is cast. If you pay the entwine cost, you choose all modes
    of the spell instead of just one.

    Example: "Entwine {2}{U}" — Pay {2}{U} to choose both modes.
    """

    name = "entwine"

    def __init__(self, cost: str | None = None):
        """Initialize Entwine keyword.

        Args:
            cost: The additional mana cost for entwining (e.g., "{2}{U}").
        """
        self.cost = cost

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Entwine."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("entwine" in k.lower() for k in keywords)
        has_oracle = bool(_ENTWINE_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_entwine(keywords: list[str]) -> bool:
        """Check if a keyword list contains entwine."""
        return any("entwine" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains entwine."""
        if not oracle_text:
            return False
        return bool(_ENTWINE_PLAIN.search(oracle_text))

    @staticmethod
    def parse_entwine_cost(oracle_text: str) -> str | None:
        """Parse the entwine cost from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Cost string (e.g., "{2}{U}") or None if not found.
        """
        match = _ENTWINE_PATTERN.search(oracle_text or "")
        if match:
            return match.group("cost").strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "EntwineKeyword | None":
        """Create EntwineKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            EntwineKeyword if entwine is found, None otherwise.
        """
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_entwine_cost(oracle_text))
        return None

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply entwine (no-op without spell casting context)."""
        return game_state

    def get_trigger_description(self) -> str:
        cost_str = self.cost or "{2}{U}"
        return f"Entwine {cost_str}: Pay to choose all modes"
