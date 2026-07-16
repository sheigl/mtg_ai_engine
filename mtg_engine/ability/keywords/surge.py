"""Surge keyword ability (CR 702.113).

Surge {cost} is an alternative cost that may be paid when you or another player
has cast a spell this turn. You pay the surge cost instead of the mana cost.
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

_SURGE_AMOUNT_PATTERN = re.compile(r"\bSurge\b\s+(?P<amount>\d+)", re.IGNORECASE)
_SURGE_COST_PATTERN = re.compile(r"\bSurge\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_SURGE_PLAIN = re.compile(r"\bSurge\b", re.IGNORECASE)


class SurgeKeyword(TriggeredKeyword):
    """Surge keyword ability.

    CR 702.113: "Surge {cost}" means 'You may pay {cost} rather than pay this
    spell's mana cost if you or another player has cast a spell this turn.'

    Example: "Surge {2}{U}" — If a spell was cast this turn, pay {2}{U} instead of mana cost.
    """

    name = "surge"
    trigger_type = "surge"

    def __init__(self, amount: int = 0):
        """Initialize Surge keyword.

        Args:
            amount: The surge amount (number of cards to discard or life to lose).
        """
        self.amount = amount

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Surge."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("surge" in k.lower() for k in keywords)
        has_oracle = bool(_SURGE_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_surge(keywords: list[str]) -> bool:
        """Check if a keyword list contains surge."""
        return any("surge" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains surge."""
        if not oracle_text:
            return False
        return bool(_SURGE_PLAIN.search(oracle_text))

    @staticmethod
    def parse_surge_amount(oracle_text: str) -> int | None:
        """Parse the surge amount from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Surge amount (int) or None if not found.
        """
        match = _SURGE_AMOUNT_PATTERN.search(oracle_text or "")
        if match:
            return int(match.group("amount"))
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "SurgeKeyword | None":
        """Create SurgeKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            SurgeKeyword if surge is found, None otherwise.
        """
        amount = cls.parse_surge_amount(oracle_text)
        if amount is not None:
            return cls(amount=amount)
        return None

    def create_trigger(self, card: "Card", controller: str, perm_id: str | None = None) -> PendingTrigger:
        """Create a surge trigger.

        Args:
            card: The card with surge being cast.
            controller: Player who is casting the spell.
            perm_id: Permanent ID if applicable (None for hand-based surge).

        Returns:
            PendingTrigger representing the surge alternative cost option.
        """
        return PendingTrigger(
            source_permanent_id=perm_id or "",
            controller=controller,
            trigger_type=self.trigger_type,
            effect_description=f"Surge {self.amount}: Pay instead of mana cost if a spell was cast this turn",
            source_card_name=card.name if card else "Unknown",
        )

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply surge (no-op without spell casting context)."""
        return game_state

    def get_trigger_description(self) -> str:
        return f"Surge {self.amount}: Pay instead of mana cost if you or another player cast a spell this turn"
