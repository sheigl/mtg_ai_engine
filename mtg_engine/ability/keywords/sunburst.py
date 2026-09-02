"""Sunburst keyword ability (CR 702.103).

Sunburst means that as this permanent enters the battlefield, if it was cast
during a certain time of day, it gets additional counters based on sun/moon
symbols in its mana cost.
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

_SUNBURST_PATTERN = re.compile(r"\bSunburst\b", re.IGNORECASE)


class SunburstKeyword(TriggeredKeyword):
    """Sunburst keyword ability.

    CR 702.103: "Sunburst" means 'As this permanent enters the battlefield, if
    it was cast during a certain time of day, put a charge counter on it for
    each sun symbol in its mana cost.' (In practice, sunburst puts +1/+1
    counters equal to colored mana symbols in the mana cost.)

    Example: "Sunburst" — Enter with counters based on colored mana in cost.
    """

    name = "sunburst"
    trigger_type = "sunburst"

    def __init__(self, sunburst_type: str = "day"):
        """Initialize Sunburst keyword.

        Args:
            sunburst_type: Type of sunburst effect ("day" or "night"). Defaults to "day".
        """
        self.sunburst_type = sunburst_type

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Sunburst."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("sunburst" in k.lower() for k in keywords)
        has_oracle = bool(_SUNBURST_PATTERN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_sunburst(keywords: list[str]) -> bool:
        """Check if a keyword list contains sunburst."""
        return any("sunburst" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains sunburst."""
        if not oracle_text:
            return False
        return bool(_SUNBURST_PATTERN.search(oracle_text))

    @staticmethod
    def parse_sunburst_type(oracle_text: str) -> str | None:
        """Parse the sunburst type from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            "day" if sunburst is found, None otherwise.
        """
        if _SUNBURST_PATTERN.search(oracle_text or ""):
            return "day"
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "SunburstKeyword | None":
        """Create SunburstKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            SunburstKeyword if sunburst is found, None otherwise.
        """
        sunburst_type = cls.parse_sunburst_type(oracle_text)
        if sunburst_type is not None:
            return cls(sunburst_type=sunburst_type)
        return None

    @staticmethod
    def count_colored_mana_symbols(mana_cost: str | None) -> int:
        """Count colored mana symbols in a mana cost string.

        Args:
            mana_cost: The mana cost string (e.g., "{2}{W}{U}").

        Returns:
            Number of colored mana symbols ({W}, {U}, {B}, {R}, {G}).
        """
        if not mana_cost:
            return 0
        # Match single-letter colored mana symbols
        colored = re.findall(r"\{[WUBRG]\}", mana_cost)
        return len(colored)

    def create_trigger(self, card: "Card", controller: str, perm_id: str | None = None) -> PendingTrigger:
        """Create a sunburst trigger.

        Args:
            card: The card with sunburst entering the battlefield.
            controller: Player who controls the permanent.
            perm_id: Permanent ID of the entering creature/artifact/enchantment.

        Returns:
            PendingTrigger representing the sunburst counter effect.
        """
        colored_count = self.count_colored_mana_symbols(card.mana_cost if card else None)
        return PendingTrigger(
            source_permanent_id=perm_id or "",
            controller=controller,
            trigger_type=self.trigger_type,
            effect_description=f"Sunburst: Enter with {colored_count} charge counters",
            source_card_name=card.name if card else "Unknown",
        )

    @staticmethod
    def apply_sunburst_counters(
        game_state: "GameState",
        permanent_id: str,
        mana_cost: str | None,
    ) -> "GameState":
        """Apply sunburst counters to a permanent on the battlefield.

        CR 702.103b: Put +1/+1 counters on creatures, charge counters on others.
        Simplified: unconditional (no day/night tracking).

        Args:
            game_state: Current game state with the permanent already on battlefield.
            permanent_id: ID of the permanent to add counters to.
            mana_cost: The mana cost string used for casting.

        Returns:
            New GameState with counters applied via model_copy.
        """
        colored_count = SunburstKeyword.count_colored_mana_symbols(mana_cost)
        if colored_count == 0:
            return game_state

        battlefield = list(game_state.battlefield)
        for i, p in enumerate(battlefield):
            if p.id == permanent_id:
                # Determine counter type based on card type
                is_creature = "creature" in (p.card.type_line or "").lower()
                counter_type = "+1/+1" if is_creature else "charge"

                new_counters = dict(p.counters) if p.counters else {}
                new_counters[counter_type] = new_counters.get(counter_type, 0) + colored_count
                battlefield[i] = p.model_copy(update={"counters": new_counters})
                break

        return game_state.model_copy(update={"battlefield": battlefield})

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply sunburst counters to a permanent on the battlefield.

        Wrapper around static method for keyword module API consistency.
        """
        mana_cost = permanent.card.mana_cost if permanent.card else None
        return self.apply_sunburst_counters(game_state, permanent.id, mana_cost)

    def get_trigger_description(self) -> str:
        return "Sunburst: Enter with charge counters equal to colored mana symbols in cost"
