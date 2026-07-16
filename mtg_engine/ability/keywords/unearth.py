"""Unearth keyword ability (CR 702.64).

Unearth {cost} is an activated ability that may be paid while the card is in a
graveyard. You return it to the battlefield tapped with a time counter on it,
and when the last time counter is removed, sacrifice it.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_UNEARTH_PATTERN = re.compile(r"\bUnearth\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_UNEARTH_PLAIN = re.compile(r"\bUnearth\b", re.IGNORECASE)


class UnearthKeyword(CostKeyword):
    """Unearth keyword ability.

    CR 702.64: "Unearth {cost}" means "{cost}, Return this card from your
    graveyard to the battlefield under your control. It enters the battlefield
    tapped with a time counter on it." At the beginning of your upkeep, remove
    a time counter from each unearthed permanent you control. When the last one
    is removed, sacrifice that permanent.

    Example: "Unearth {2}{B}" — Pay {2}{B} to return this card from graveyard tapped with 1 time counter.
    """

    name = "unearth"

    def __init__(self, cost: str | None = None):
        """Initialize Unearth keyword.

        Args:
            cost: The mana cost for unearthing (e.g., "{2}{B}").
        """
        self.cost = cost

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Unearth."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("unearth" in k.lower() for k in keywords)
        has_oracle = bool(_UNEARTH_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_unearth(keywords: list[str]) -> bool:
        """Check if a keyword list contains unearth."""
        return any("unearth" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains unearth."""
        if not oracle_text:
            return False
        return bool(_UNEARTH_PLAIN.search(oracle_text))

    @staticmethod
    def parse_unearth_cost(oracle_text: str) -> str | None:
        """Parse the unearth cost from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Cost string (e.g., "{2}{B}") or None if not found.
        """
        match = _UNEARTH_PATTERN.search(oracle_text or "")
        if match:
            return match.group("cost").strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "UnearthKeyword | None":
        """Create UnearthKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            UnearthKeyword if unearth is found, None otherwise.
        """
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_unearth_cost(oracle_text))
        return None

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply unearth (no-op without graveyard context)."""
        return game_state

    def get_trigger_description(self) -> str:
        cost_str = self.cost or "{2}{B}"
        return f"Unearth {cost_str}: Return from graveyard tapped with 1 time counter"
