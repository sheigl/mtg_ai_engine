"""Suspend keyword ability (CR 702.65).

Suspend {N}{cost} is a timed ability that lets you exile a card from your hand,
then after N turns have passed, cast it by paying the cost without paying its
mana cost.
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

_SUSPEND_PATTERN = re.compile(
    r"\bSuspend\b\s+(?P<count>\d+)\s*(?:(?P<cost>(?:\{[^}]+\})+))?",
    re.IGNORECASE,
)
_SUSPEND_PLAIN = re.compile(r"\bSuspend\b", re.IGNORECASE)


class SuspendKeyword(TriggeredKeyword):
    """Suspend keyword ability.

    CR 702.65: "Suspend N{cost}" means 'As long as this card is in your hand,
    you may pay {cost} and exile it with N time counters on it.', 'At the
    beginning of your upkeep, remove a time counter from this card.', and
    'If the last one is removed, cast this card without paying its mana cost.'"

    Example: "Suspend 3{2}{U}" — Exile with 3 time counters, pay {2}{U} to suspend.
    """

    name = "suspend"
    trigger_type = "suspend"

    def __init__(self, count: int = 1, cost: str | None = None):
        """Initialize Suspend keyword.

        Args:
            count: Number of time counters (N in suspend N).
            cost: The cost to pay when suspending the card.
        """
        self.count = count
        self.cost = cost

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Suspend."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("suspend" in k.lower() for k in keywords)
        has_oracle = bool(_SUSPEND_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_suspend(keywords: list[str]) -> bool:
        """Check if a keyword list contains suspend."""
        return any("suspend" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains suspend."""
        if not oracle_text:
            return False
        return bool(_SUSPEND_PLAIN.search(oracle_text))

    @staticmethod
    def parse_suspend_params(oracle_text: str) -> tuple[int, str | None]:
        """Parse the suspend count and cost from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Tuple of (count, cost_string_or_None).
        """
        match = _SUSPEND_PATTERN.search(oracle_text or "")
        if match:
            count = int(match.group("count"))
            cost = match.group("cost")
            return count, cost.strip() if cost else None
        return 1, None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "SuspendKeyword | None":
        """Create SuspendKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            SuspendKeyword if suspend is found, None otherwise.
        """
        if cls.from_oracle_text(oracle_text):
            count, cost = cls.parse_suspend_params(oracle_text)
            return cls(count=count, cost=cost)
        return None

    def create_trigger(self, card: "Card", controller: str, perm_id: str | None = None) -> "PendingTrigger":
        """Create a suspend trigger.

        Args:
            card: The suspended card.
            controller: Player who suspended the card.
            perm_id: Permanent ID if applicable (None for hand-based suspend).

        Returns:
            PendingTrigger representing the suspend ability.
        """
        return PendingTrigger(
            source_permanent_id=perm_id or "",
            controller=controller,
            trigger_type=self.trigger_type,
            effect_description=f"Suspend {self.count}: Exile with {self.count} time counters",
            source_card_name=card.name if card else "Unknown",
        )

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply suspend (no-op without hand/exile context)."""
        return game_state

    def get_trigger_description(self) -> str:
        cost_str = self.cost or ""
        return f"Suspend {self.count}{cost_str}: Exile with {self.count} time counters, cast when last counter removed"
