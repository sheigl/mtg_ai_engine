"""Replicate keyword ability (CR 702.51).

Replicate {cost} is a triggered ability that triggers as this permanent enters
the battlefield. For each copy, you may pay the replicate cost to make another
copy of the spell.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_REPLICATE_PATTERN = re.compile(r"\bReplicate\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_REPLICATE_PLAIN = re.compile(r"\bReplicate\b", re.IGNORECASE)


class ReplicateKeyword(CostKeyword):
    """Replicate keyword ability.

    CR 702.51: "Replicate {cost}" means 'As this permanent enters the
    battlefield, if it was cast, you may pay {cost}. For each time you do, copy
    this spell and you may choose new targets for the copy.'

    Example: "Replicate {X}{U}" — Pay {X}{U} to make copies of this spell.
    """

    name = "replicate"

    def __init__(self, cost: str | None = None):
        """Initialize Replicate keyword.

        Args:
            cost: The mana cost for replicating (e.g., "{X}{U}").
        """
        self.cost = cost

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Replicate."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("replicate" in k.lower() for k in keywords)
        has_oracle = bool(_REPLICATE_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_replicate(keywords: list[str]) -> bool:
        """Check if a keyword list contains replicate."""
        return any("replicate" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains replicate."""
        if not oracle_text:
            return False
        return bool(_REPLICATE_PLAIN.search(oracle_text))

    @staticmethod
    def parse_replicate_cost(oracle_text: str) -> str | None:
        """Parse the replicate cost from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Cost string (e.g., "{X}{U}") or None if not found.
        """
        match = _REPLICATE_PATTERN.search(oracle_text or "")
        if match:
            return match.group("cost").strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "ReplicateKeyword | None":
        """Create ReplicateKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            ReplicateKeyword if replicate is found, None otherwise.
        """
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_replicate_cost(oracle_text))
        return None

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply replicate (no-op without spell casting context)."""
        return game_state

    def get_trigger_description(self) -> str:
        cost_str = self.cost or "{X}{U}"
        return f"Replicate {cost_str}: Pay to make a copy of this spell as it enters"
