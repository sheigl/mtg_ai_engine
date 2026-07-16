"""Buyback keyword ability (CR 702.28).

Buyback {cost} is an additional cost that may be paid as a sorcery spell
is cast. If you pay the buyback cost, the spell returns to your hand instead
of going to your graveyard when it resolves.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_BUYBACK_PATTERN = re.compile(r"\bBuyback\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_BUYBACK_PLAIN = re.compile(r"\bBuyback\b", re.IGNORECASE)


class BuybackKeyword(CostKeyword):
    """Buyback keyword ability.

    CR 702.28: "Buyback {cost}" is an additional cost that may be paid as a
    sorcery spell is cast. If you pay the buyback cost, return this spell to
    its owner's hand instead of putting it into their graveyard when it resolves.

    Example: "Buyback {3}{B}" — Pay {3}{B} to return this spell to your hand.
    """

    name = "buyback"

    def __init__(self, cost: str | None = None):
        """Initialize Buyback keyword.

        Args:
            cost: The additional mana cost for buyback (e.g., "{3}{B}").
        """
        self.cost = cost

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Buyback."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("buyback" in k.lower() for k in keywords)
        has_oracle = bool(_BUYBACK_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_buyback(keywords: list[str]) -> bool:
        """Check if a keyword list contains buyback."""
        return any("buyback" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains buyback."""
        if not oracle_text:
            return False
        return bool(_BUYBACK_PLAIN.search(oracle_text))

    @staticmethod
    def parse_buyback_cost(oracle_text: str) -> str | None:
        """Parse the buyback cost from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Cost string (e.g., "{3}{B}") or None if not found.
        """
        match = _BUYBACK_PATTERN.search(oracle_text or "")
        if match:
            return match.group("cost").strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "BuybackKeyword | None":
        """Create BuybackKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            BuybackKeyword if buyback is found, None otherwise.
        """
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_buyback_cost(oracle_text))
        return None

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply buyback (no-op without spell resolution context)."""
        return game_state

    def get_trigger_description(self) -> str:
        cost_str = self.cost or "{3}{B}"
        return f"Buyback {cost_str}: Pay to return this spell to your hand"
