"""Bloodthirst keyword ability (CR 702.31).

Bloodthirst N means that if a creature dealt damage to an opponent this turn,
this permanent enters the battlefield with N +1/+1 counters on it.
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

_BLOODTHIRST_PATTERN = re.compile(r"\bBloodthirst\b\s+(?P<amount>\d+)", re.IGNORECASE)
_BLOODTHIRST_PLAIN = re.compile(r"\bBloodthirst\b", re.IGNORECASE)


class BloodthirstKeyword(TriggeredKeyword):
    """Bloodthirst keyword ability.

    CR 702.31: "Bloodthirst N" means 'If an opponent was dealt combat damage this
    turn, this permanent enters the battlefield with N +1/+1 counters on it.'

    Example: "Bloodthirst 2" — If opponent took combat damage, enter with two +1/+1 counters.
    """

    name = "bloodthirst"
    trigger_type = "bloodthirst"

    def __init__(self, amount: int = 0):
        """Initialize Bloodthirst keyword.

        Args:
            amount: Number of +1/+1 counters to put on the creature if condition is met.
        """
        self.amount = amount

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Bloodthirst."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("bloodthirst" in k.lower() for k in keywords)
        has_oracle = bool(_BLOODTHIRST_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_bloodthirst(keywords: list[str]) -> bool:
        """Check if a keyword list contains bloodthirst."""
        return any("bloodthirst" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains bloodthirst."""
        if not oracle_text:
            return False
        return bool(_BLOODTHIRST_PLAIN.search(oracle_text))

    @staticmethod
    def parse_bloodthirst_amount(oracle_text: str) -> int | None:
        """Parse the bloodthirst amount from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Amount of +1/+1 counters, or None if not found.
        """
        match = _BLOODTHIRST_PATTERN.search(oracle_text or "")
        if match:
            return int(match.group("amount"))
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "BloodthirstKeyword | None":
        """Create BloodthirstKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            BloodthirstKeyword if bloodthirst is found, None otherwise.
        """
        amount = cls.parse_bloodthirst_amount(oracle_text)
        if amount is not None:
            return cls(amount=amount)
        return None

    def create_trigger(self, card: "Card", controller: str, perm_id: str | None = None) -> PendingTrigger:
        """Create a bloodthirst trigger.

        Args:
            card: The card with bloodthirst entering the battlefield.
            controller: Player who controls the permanent.
            perm_id: Permanent ID of the entering creature.

        Returns:
            PendingTrigger representing the bloodthirst counter effect.
        """
        return PendingTrigger(
            source_permanent_id=perm_id or "",
            controller=controller,
            trigger_type=self.trigger_type,
            effect_description=f"Bloodthirst {self.amount}: If opponent took combat damage, enter with {self.amount} +1/+1 counters",
            source_card_name=card.name if card else "Unknown",
        )

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply bloodthirst (no-op without combat damage tracking)."""
        return game_state

    def get_trigger_description(self) -> str:
        return f"Bloodthirst {self.amount}: If opponent took combat damage this turn, enter with {self.amount} +1/+1 counters"
