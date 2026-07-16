"""Extort keyword ability (CR 702.104).

Extort {cost} is a triggered ability that triggers whenever you cast a spell.
You may pay the extort cost, and if you do, each opponent loses 1 life and you
gain 1 life for each opponent.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_EXTORT_PATTERN = re.compile(r"\bExtort\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_EXTORT_PLAIN = re.compile(r"\bExtort\b", re.IGNORECASE)


class ExtortKeyword(CostKeyword):
    """Extort keyword ability.

    CR 702.104: "Extort {cost}" means 'Whenever you cast a spell, you may pay
    {cost}. If you do, each opponent loses 1 life and you gain 1 life for each
    opponent.'

    Example: "Extort {W}{B}" — Whenever you cast a spell, pay {W}{B} to make each opponent lose 1 and you gain 1.
    """

    name = "extort"

    def __init__(self, cost: str | None = None):
        """Initialize Extort keyword.

        Args:
            cost: The mana cost for extorting (e.g., "{W}{B}").
        """
        self.cost = cost

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Extort."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("extort" in k.lower() for k in keywords)
        has_oracle = bool(_EXTORT_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_extort(keywords: list[str]) -> bool:
        """Check if a keyword list contains extort."""
        return any("extort" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains extort."""
        if not oracle_text:
            return False
        return bool(_EXTORT_PLAIN.search(oracle_text))

    @staticmethod
    def parse_extort_cost(oracle_text: str) -> str | None:
        """Parse the extort cost from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Cost string (e.g., "{W}{B}") or None if not found.
        """
        match = _EXTORT_PATTERN.search(oracle_text or "")
        if match:
            return match.group("cost").strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "ExtortKeyword | None":
        """Create ExtortKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            ExtortKeyword if extort is found, None otherwise.
        """
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_extort_cost(oracle_text))
        return None

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply extort (no-op without spell casting context)."""
        return game_state

    def get_trigger_description(self) -> str:
        cost_str = self.cost or "{W}{B}"
        return f"Extort {cost_str}: Whenever you cast a spell, pay to make each opponent lose 1 life and you gain 1"
