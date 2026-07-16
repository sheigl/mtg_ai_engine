"""Afterlife keyword ability (CR 702.108).

Afterlife N means that when this permanent dies, create N afterlife counters'
worth of Spirit creature tokens.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import TriggeredKeyword
from mtg_engine.models.game import PendingTrigger

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Card, Permanent

_AFTERLIFE_PATTERN = re.compile(r"\bAfterlife\b\s+(?P<count>\d+)", re.IGNORECASE)
_AFTERLIFE_PLAIN = re.compile(r"\bAfterlife\b", re.IGNORECASE)


class AfterlifeKeyword(TriggeredKeyword):
    """Afterlife keyword ability.

    CR 702.108: "Afterlife N" means 'When this permanent dies, create N 0/0
    white Spirit creature tokens with afterlife 1.' (The created tokens have
    afterlife 1, so when they die, they create another 0/0 white Spirit token.)

    Example: "Afterlife 2" — When it dies, create two 0/0 white Spirit tokens.
    """

    name = "afterlife"
    trigger_type = "afterlife"

    def __init__(self, count: int = 1):
        """Initialize Afterlife keyword.

        Args:
            count: Number of Spirit tokens to create when the permanent dies.
        """
        self.count = count

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Afterlife."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("afterlife" in k.lower() for k in keywords)
        has_oracle = bool(_AFTERLIFE_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_afterlife(keywords: list[str]) -> bool:
        """Check if a keyword list contains afterlife."""
        return any("afterlife" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains afterlife."""
        if not oracle_text:
            return False
        return bool(_AFTERLIFE_PLAIN.search(oracle_text))

    @staticmethod
    def parse_afterlife_count(oracle_text: str) -> int | None:
        """Parse the afterlife count from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Count of Spirit tokens to create, or None if not found.
        """
        match = _AFTERLIFE_PATTERN.search(oracle_text or "")
        if match:
            return int(match.group("count"))
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "AfterlifeKeyword | None":
        """Create AfterlifeKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            AfterlifeKeyword if afterlife is found, None otherwise.
        """
        count = cls.parse_afterlife_count(oracle_text)
        if count is not None:
            return cls(count=count)
        return None

    def create_trigger(self, card: "Card", controller: str, perm_id: str | None = None) -> "PendingTrigger":
        """Create an afterlife trigger.

        Args:
            card: The card with afterlife that died.
            controller: Player who controlled the permanent.
            perm_id: Permanent ID of the dead creature.

        Returns:
            PendingTrigger representing the afterlife token creation.
        """
        return PendingTrigger(
            source_permanent_id=perm_id or "",
            controller=controller,
            trigger_type=self.trigger_type,
            effect_description=f"Afterlife {self.count}: Create {self.count} 0/0 white Spirit tokens",
            source_card_name=card.name if card else "Unknown",
        )

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply afterlife (no-op without death context)."""
        return game_state

    def get_trigger_description(self) -> str:
        return f"Afterlife {self.count}: When this dies, create {self.count} 0/0 white Spirit tokens"
