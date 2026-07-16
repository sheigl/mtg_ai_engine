"""
Leaves-the-Battlefield (LTB) keyword triggers.

KW-03: Implements LTB keyword abilities that trigger when a permanent
leaves the battlefield. Handles "dies", "leaves the battlefield", etc.
"""
from __future__ import annotations
import logging
import re
import uuid
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent, PendingTrigger

logger = logging.getLogger(__name__)

# LTB trigger patterns
_LTB_PATTERNS = [
    re.compile(r"when(?:ever)? (?:this|~) leaves (?:the )?battlefield", re.IGNORECASE),
    re.compile(r"when(?:ever)? (?:a|an) (\w+) leaves (?:the )?battlefield", re.IGNORECASE),
    re.compile(r"when(?:ever)? (?:this|~|a|an \w+) dies", re.IGNORECASE),
    re.compile(r"whenever (?:this|~) leaves (?:the )?battlefield", re.IGNORECASE),
    re.compile(r"whenever (?:a|an) (\w+) dies", re.IGNORECASE),
]


class LeaveBattlefieldKeyword(TriggeredKeyword):
    """Keyword ability that triggers when a permanent leaves the battlefield.

    Handles LTB triggers including:
    - "When this leaves the battlefield, <effect>"
    - "Whenever a creature dies, <effect>"
    - "Whenever ~ is put into a graveyard from the battlefield, <effect>"
    """

    name = "ltb"

    def __init__(
        self,
        effect: str = "",
        trigger_type: str = "self",
        card_type_filter: str | None = None,
        zone_filter: str | None = None,
    ):
        """Initialize LTB keyword.

        Args:
            effect: The effect text to apply on trigger.
            trigger_type: "self" for self-referential, "any" for any matching permanent.
            card_type_filter: Optional card type to filter (e.g., "creature").
            zone_filter: Optional destination zone filter ("graveyard", "exile", None for any).
        """
        self.effect = effect
        self.trigger_type = trigger_type
        self.card_type_filter = card_type_filter
        self.zone_filter = zone_filter

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this permanent has an LTB trigger."""
        oracle = permanent.card.oracle_text or ""
        return any(pattern.search(oracle) for pattern in _LTB_PATTERNS)

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply LTB effect when a permanent leaves the battlefield."""
        if not self.effect:
            return game_state

        controller = permanent.controller
        logger.info(
            "LTB trigger from %s (%s): %s",
            permanent.card.name,
            controller,
            self.effect,
        )
        return game_state

    def create_trigger(
        self,
        game_state: "GameState",
        source_perm: "Permanent",
        leaving_perm: "Permanent",
        to_zone: str = "graveyard",
    ) -> "PendingTrigger | None":
        """Create a PendingTrigger for an LTB event.

        Args:
            game_state: Current game state.
            source_perm: The permanent with the LTB ability.
            leaving_perm: The permanent that left the battlefield.
            to_zone: Destination zone ("graveyard", "exile", etc.).

        Returns:
            PendingTrigger if conditions are met, None otherwise.
        """
        # Self-referential trigger: "when this leaves/dies"
        if self.trigger_type == "self":
            if source_perm.id != leaving_perm.id:
                return None

        # Type filter: "whenever a creature dies"
        if self.card_type_filter:
            type_line = leaving_perm.card.type_line.lower()
            if self.card_type_filter.lower() not in type_line:
                return None

        # Zone filter: "dies" means to graveyard
        if self.zone_filter and to_zone != self.zone_filter:
            return None

        # "Dies" specifically means from battlefield to graveyard
        if "dies" in self.effect.lower() and to_zone != "graveyard":
            return None

        from mtg_engine.models.game import PendingTrigger

        is_optional = self.effect.lower().startswith("you may")
        return PendingTrigger(
            id=str(uuid.uuid4()),
            source_permanent_id=source_perm.id,
            controller=source_perm.controller,
            trigger_type="ltb",
            effect_description=self.effect,
            source_card_name=source_perm.card.name,
            is_optional=is_optional,
        )

    def get_trigger_description(self) -> str:
        return f"LTB: {self.effect}"


class DiesKeyword(LeaveBattlefieldKeyword):
    """Dies: Triggers when a creature is put into a graveyard from the battlefield.

    CR 700.1: "Dies" means "is put into a graveyard from the battlefield."
    """

    name = "dies"

    def __init__(self, effect: str = "", card_type_filter: str | None = "creature"):
        super().__init__(
            effect=effect,
            trigger_type="any",
            card_type_filter=card_type_filter,
            zone_filter="graveyard",
        )

    def get_trigger_description(self) -> str:
        return f"Dies: {self.effect}"


class UndyingKeyword(LeaveBattlefieldKeyword):
    """Undying: Returns dead creature with +1/+1 counters.

    CR 702.51: "When undead creature with undying dies, if it had no +1/+1
    counters on it, return it to the battlefield under its owner's control
    with a number of +1/+1 counters on it equal to its power and toughness."
    """

    name = "undying"

    def __init__(self, effect: str = ""):
        super().__init__(effect=effect, trigger_type="self", zone_filter="graveyard")

    def create_trigger(
        self,
        game_state: "GameState",
        source_perm: "Permanent",
        leaving_perm: "Permanent",
        to_zone: str = "graveyard",
    ) -> "PendingTrigger | None":
        """Create trigger only if the dying creature had no +1/+1 counters."""
        counters = leaving_perm.counters or {}
        if counters.get("+1/+1", 0) > 0:
            return None
        return super().create_trigger(game_state, source_perm, leaving_perm, to_zone)

    def get_trigger_description(self) -> str:
        return f"Undying: {self.effect}"
