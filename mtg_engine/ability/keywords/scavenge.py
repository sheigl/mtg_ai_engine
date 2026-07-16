"""Scavenge keyword ability (CR 702.106).

Scavenge {cost} is an activated ability that lets you exile a card from your
graveyard and pay the scavenge cost to put +1/+1 counters on a creature equal
to the exiled card's power.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_SCAVENGE_PATTERN = re.compile(r"\bScavenge\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_SCAVENGE_PLAIN = re.compile(r"\bScavenge\b", re.IGNORECASE)


class ScavengeKeyword(CostKeyword):
    """Scavenge keyword ability.

    CR 702.106: "Scavenge {cost}" means "{cost}, Exile this card from your
    graveyard: Put X +1/+1 counters on target creature, where X is this card's
    power."

    Example: "Scavenge {2}{G}" — Pay {2}{G} to exile and give creature +1/+1 per exiled card's power.
    """

    name = "scavenge"

    def __init__(self, cost: str | None = None):
        """Initialize Scavenge keyword.

        Args:
            cost: The mana cost for scavenging (e.g., "{2}{G}").
        """
        self.cost = cost

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Scavenge."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("scavenge" in k.lower() for k in keywords)
        has_oracle = bool(_SCAVENGE_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_scavenge(keywords: list[str]) -> bool:
        """Check if a keyword list contains scavenge."""
        return any("scavenge" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains scavenge."""
        if not oracle_text:
            return False
        return bool(_SCAVENGE_PLAIN.search(oracle_text))

    @staticmethod
    def parse_scavenge_cost(oracle_text: str) -> str | None:
        """Parse the scavenge cost from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Cost string (e.g., "{2}{G}") or None if not found.
        """
        match = _SCAVENGE_PATTERN.search(oracle_text or "")
        if match:
            return match.group("cost").strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "ScavengeKeyword | None":
        """Create ScavengeKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            ScavengeKeyword if scavenge is found, None otherwise.
        """
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_scavenge_cost(oracle_text))
        return None

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply scavenge (no-op without graveyard context)."""
        return game_state

    def get_trigger_description(self) -> str:
        cost_str = self.cost or "{2}{G}"
        return f"Scavenge {cost_str}: Exile from graveyard, put +1/+1 counters on creature equal to its power"
