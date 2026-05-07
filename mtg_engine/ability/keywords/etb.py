"""
Enters-the-Battlefield (ETB) keyword triggers.

KW-02: Implements ETB keyword abilities that trigger when a permanent
enters the battlefield. Handles patterns like "When ~ enters, draw a card".
"""
from __future__ import annotations
import logging
import re
import uuid
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Card, Permanent, PendingTrigger

logger = logging.getLogger(__name__)

# ETB trigger patterns
_ETB_PATTERNS = [
    re.compile(r"when(?:ever)? (?:this|~) enters (?:the )?battlefield", re.IGNORECASE),
    re.compile(r"when(?:ever)? (?:a|an) (\w+) enters (?:the )?battlefield", re.IGNORECASE),
    re.compile(r"when(?:ever)? (?:a|an) (\w+) enters", re.IGNORECASE),
    re.compile(r"whenever (?:this|~) enters (?:the )?battlefield", re.IGNORECASE),
    re.compile(r"whenever (?:a|an) (\w+) enters (?:the )?battlefield", re.IGNORECASE),
]


class EtbKeyword(TriggeredKeyword):
    """Keyword ability that triggers when a permanent enters the battlefield.

    Handles ETB triggers including:
    - "When this enters the battlefield, <effect>"
    - "Whenever a creature enters the battlefield, <effect>"
    - Landfall: "Whenever a land enters the battlefield under your control, <effect>"
    """

    name = "etb"

    def __init__(
        self,
        effect: str = "",
        trigger_type: str = "self",
        card_type_filter: str | None = None,
    ):
        """Initialize ETB keyword.

        Args:
            effect: The effect text to apply on trigger.
            trigger_type: "self" for self-referential, "any" for any matching permanent.
            card_type_filter: Optional card type to filter (e.g., "creature", "land").
        """
        self.effect = effect
        self.trigger_type = trigger_type
        self.card_type_filter = card_type_filter

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this permanent has an ETB trigger."""
        oracle = permanent.card.oracle_text or ""
        return any(pattern.search(oracle) for pattern in _ETB_PATTERNS)

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply ETB effect when a permanent enters the battlefield."""
        if not self.effect:
            return game_state

        controller = permanent.controller
        logger.info(
            "ETB trigger from %s (%s): %s",
            permanent.card.name,
            controller,
            self.effect,
        )
        return game_state

    def create_trigger(
        self,
        game_state: "GameState",
        source_perm: "Permanent",
        entering_perm: "Permanent",
    ) -> "PendingTrigger | None":
        """Create a PendingTrigger for an ETB event.

        Args:
            game_state: Current game state.
            source_perm: The permanent with the ETB ability.
            entering_perm: The permanent that entered the battlefield.

        Returns:
            PendingTrigger if conditions are met, None otherwise.
        """
        # Self-referential trigger: "when this enters"
        if self.trigger_type == "self":
            if source_perm.id != entering_perm.id:
                return None

        # Type filter: "whenever a creature enters"
        if self.card_type_filter:
            type_line = entering_perm.card.type_line.lower()
            if self.card_type_filter.lower() not in type_line:
                return None

        from mtg_engine.models.game import PendingTrigger

        is_optional = self.effect.lower().startswith("you may")
        return PendingTrigger(
            id=str(uuid.uuid4()),
            source_permanent_id=source_perm.id,
            controller=source_perm.controller,
            trigger_type="etb",
            effect_description=self.effect,
            source_card_name=source_perm.card.name,
            is_optional=is_optional,
        )

    def get_trigger_description(self) -> str:
        return f"ETB: {self.effect}"


class LandfallKeyword(EtbKeyword):
    """Landfall: Triggers whenever a land enters the battlefield.

    CR 702.44: Landfall is a triggered ability: "Whenever a land enters
    the battlefield under your control, [effect]."
    """

    name = "landfall"

    def __init__(self, effect: str = ""):
        super().__init__(effect=effect, trigger_type="any", card_type_filter="land")

    def create_trigger(
        self,
        game_state: "GameState",
        source_perm: "Permanent",
        entering_perm: "Permanent",
    ) -> "PendingTrigger | None":
        """Create a PendingTrigger for a landfall event."""
        if "land" not in entering_perm.card.type_line.lower():
            return None

        from mtg_engine.models.game import PendingTrigger

        return PendingTrigger(
            id=str(uuid.uuid4()),
            source_permanent_id=source_perm.id,
            controller=source_perm.controller,
            trigger_type="landfall",
            effect_description=self.effect,
            source_card_name=source_perm.card.name,
            is_optional=self.effect.lower().startswith("you may"),
        )

    def get_trigger_description(self) -> str:
        return f"Landfall: {self.effect}"
