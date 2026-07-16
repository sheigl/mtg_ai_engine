"""Transmute keyword action (CR 702.68).

Transmute {cost} means "Discard target nonland card from your hand, pay {cost},
then search your library for up to two cards with the same converted mana cost
as that card and reveal those cards. Put them into your hand and the rest on
the bottom of your library in a random order."
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_TRANSMUTE_PATTERN = re.compile(r"\bTransmute\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_TRANSMUTE_PLAIN = re.compile(r"\bTransmute\b", re.IGNORECASE)


class TransmuteKeyword(CostKeyword):
    """Transmute keyword ability.

    CR 702.68: "Transmute {cost}" means "Discard target nonland card from your hand,
    pay {cost}, then search your library for up to two cards with the same converted
    mana cost as that card and reveal those cards. Put them into your hand and the
    rest on the bottom of your library in a random order."

    Example: "Transmute {2}" — Discard target nonland card from your hand, pay {2},
    then search for up to two cards with the same CMV as that card.
    """

    name = "transmute"

    def __init__(self, cost: str | None = None):
        """Initialize Transmute keyword.

        Args:
            cost: The additional mana cost for transmuting (e.g., "{2}").
        """
        self.cost = cost

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Transmute."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("transmute" in k.lower() for k in keywords)
        has_oracle = bool(_TRANSMUTE_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_transmute(keywords: list[str]) -> bool:
        """Check if a keyword list contains transmute."""
        return any("transmute" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains transmute."""
        if not oracle_text:
            return False
        return bool(_TRANSMUTE_PLAIN.search(oracle_text))

    @staticmethod
    def parse_transmute_cost(oracle_text: str) -> str | None:
        """Parse the transmute cost from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Cost string (e.g., "{2}") or None if not found.
        """
        match = _TRANSMUTE_PATTERN.search(oracle_text or "")
        if match:
            return match.group("cost").strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "TransmuteKeyword | None":
        """Create TransmuteKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            TransmuteKeyword if transmute is found, None otherwise.
        """
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_transmute_cost(oracle_text))
        return None

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply transmute (no-op without hand/library context)."""
        return game_state

    def get_trigger_description(self) -> str:
        cost_str = self.cost or "{2}"
        return f"Transmute {cost_str}: Discard card, search for same CMV cards"
