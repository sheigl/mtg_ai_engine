"""Undying keyword ability (CR 702.51).

Undying is a triggered ability that functions when the creature with undying
dies. If it had no +1/+1 counters on it, its controller returns it to the
battlefield under their control with +1/+1 counters equal to its power and toughness.
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

_UNDYING_PATTERN = re.compile(r"\bUndying\b", re.IGNORECASE)


class UndyingKeyword(TriggeredKeyword):
    """Undying keyword ability.

    CR 702.51: "When a creature with undying dies, if it had no +1/+1 counters on it,
    return it to the battlefield under its owner's control with a number of +1/+1
    counters on it equal to its power and toughness."

    Example: A 2/2 creature with undying that dies without +1/+1 counters returns
    with four +1/+1 counters (becoming a 6/6).
    """

    name = "undying"
    trigger_condition = "leaves_battlefield"

    def __init__(self, effect: str = ""):
        """Initialize Undying keyword.

        Args:
            effect: The effect text to apply on trigger.
        """
        self.effect = effect

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Undying."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("undying" in k.lower() for k in keywords)
        has_oracle = bool(_UNDYING_PATTERN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_undying(keywords: list[str]) -> bool:
        """Check if a keyword list contains undying."""
        return any("undying" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains undying."""
        if not oracle_text:
            return False
        return bool(_UNDYING_PATTERN.search(oracle_text))

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply undying (no-op without death context)."""
        return game_state

    def get_counter_count(self, permanent: "Permanent") -> int:
        """Calculate the number of +1/+1 counters to add.

        The count equals power + toughness of the creature.

        Args:
            permanent: The dying creature.

        Returns:
            Number of +1/+1 counters (power + toughness).
        """
        try:
            power = int(permanent.card.power or 0)
            toughness = int(permanent.card.toughness or 0)
        except (ValueError, TypeError):
            return 0
        return power + toughness

    def create_trigger(
        self,
        game_state: "GameState",
        source_perm: "Permanent",
        leaving_perm: "Permanent",
        to_zone: str = "graveyard",
    ) -> "PendingTrigger | None":
        """Create trigger only if the dying creature has no +1/+1 counters.

        Args:
            game_state: Current game state.
            source_perm: The permanent with undying ability.
            leaving_perm: The permanent that left the battlefield.
            to_zone: Destination zone ("graveyard", "exile", etc.).

        Returns:
            PendingTrigger if conditions are met, None otherwise.
        """
        # Self-referential: only triggers for this specific creature
        if source_perm.id != leaving_perm.id:
            return None

        # Only triggers when going to graveyard ("dies")
        if to_zone != "graveyard":
            return None

        # Undying only fires if there are no +1/+1 counters
        counters = leaving_perm.counters or {}
        if counters.get("+1/+1", 0) > 0:
            logger.debug(
                "Undying on %s does not fire — already has +1/+1 counter(s)",
                leaving_perm.card.name,
            )
            return None

        from mtg_engine.models.game import PendingTrigger

        counter_count = self.get_counter_count(leaving_perm)
        effect_text = self.effect or (
            f"Return {leaving_perm.card.name} to the battlefield with "
            f"{counter_count} +1/+1 counters."
        )
        return PendingTrigger(
            id=str(uuid.uuid4()),
            source_permanent_id=source_perm.id,
            controller=source_perm.controller,
            trigger_type="undying",
            effect_description=effect_text,
            source_card_name=source_perm.card.name,
            is_optional=False,
        )

    def get_trigger_description(self) -> str:
        return "Undying: When this dies with no +1/+1 counters, return it with P+T counters"
