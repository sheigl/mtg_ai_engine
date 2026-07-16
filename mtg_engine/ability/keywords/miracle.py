"""Miracle keyword ability (CR 702.41).

Miracle {cost} is an alternative cost that may be paid when you draw a card,
but only if it would be the first card drawn that turn. You reveal the card
and cast it by paying its miracle cost instead of its mana cost.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_MIRACLE_PATTERN = re.compile(r"\bMiracle\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_MIRACLE_PLAIN = re.compile(r"\bMiracle\b", re.IGNORECASE)


class MiracleKeyword(CostKeyword):
    """Miracle keyword ability.

    CR 702.41: "Miracle {cost}" means 'If you draw this card as the first card
    drawn by you this turn, you may reveal it and cast it by paying {cost}
    rather than paying its mana cost.'

    Example: "Miracle {1}{U}" — If drawn first this turn, pay {1}{U} to cast.
    """

    name = "miracle"

    def __init__(self, cost: str | None = None):
        """Initialize Miracle keyword.

        Args:
            cost: The alternative mana cost for miracle (e.g., "{1}{U}").
        """
        self.cost = cost

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Miracle."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("miracle" in k.lower() for k in keywords)
        has_oracle = bool(_MIRACLE_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_miracle(keywords: list[str]) -> bool:
        """Check if a keyword list contains miracle."""
        return any("miracle" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains miracle."""
        if not oracle_text:
            return False
        return bool(_MIRACLE_PLAIN.search(oracle_text))

    @staticmethod
    def parse_miracle_cost(oracle_text: str) -> str | None:
        """Parse the miracle cost from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Cost string (e.g., "{1}{U}") or None if not found.
        """
        match = _MIRACLE_PATTERN.search(oracle_text or "")
        if match:
            return match.group("cost").strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "MiracleKeyword | None":
        """Create MiracleKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            MiracleKeyword if miracle is found, None otherwise.
        """
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_miracle_cost(oracle_text))
        return None

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply miracle (no-op without draw context)."""
        return game_state

    def get_trigger_description(self) -> str:
        cost_str = self.cost or "{1}{U}"
        return f"Miracle {cost_str}: If drawn first this turn, pay to cast instead of mana cost"
