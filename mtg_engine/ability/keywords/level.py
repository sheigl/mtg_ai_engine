"""
Level Up keyword ability.

KW-05: Implements the Level Up mechanic.
CR 702.44: "Level up [{cost}] — [effect]. Level N — [static ability]."
Level up puts level counters on the creature. The level abilities activate
based on the number of level counters.
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)

# Level Up patterns (handle both en-dash and em-dash, multi-part costs like {2}{G})
_LEVEL_UP_PATTERN = re.compile(r"level\s*up\s+(\{[^}]+\}+(?:\s*\{[^}]+\})*)\s*[–—-]\s*(.+)", re.IGNORECASE)
_LEVEL_N_PATTERN = re.compile(r"level\s+(\d+)\s*[–—-]\s*(.+)", re.IGNORECASE)


class LevelUpKeyword(TriggeredKeyword):
    """Level Up keyword ability.

    CR 702.44: Level up is an activated ability that puts level counters
    on a creature. Level N abilities are static abilities that apply
    based on the number of level counters.

    Example:
        Level up {2}{G} — Put two +1/+1 counters on this creature.
        Level 2 — Whenever a creature enters the battlefield, draw a card.
        Level 4 — Flying
        Level 6 — Trample
    """

    name = "level up"

    def __init__(
        self,
        cost: str = "",
        effect: str = "",
        level_abilities: list[tuple[int, str]] | None = None,
    ):
        """Initialize Level Up keyword.

        Args:
            cost: The level up cost (e.g., "{2}{G}").
            effect: The level up effect (usually puts counters).
            level_abilities: List of (level, ability_text) tuples for level N abilities.
        """
        self.cost = cost
        self.effect = effect
        self.level_abilities: list[tuple[int, str]] = level_abilities or []

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this permanent has Level Up."""
        oracle = permanent.card.oracle_text or ""
        return bool(_LEVEL_UP_PATTERN.search(oracle))

    def get_level(self, permanent: "Permanent") -> int:
        """Get current level based on level counters."""
        counters = permanent.counters or {}
        return counters.get("level", 0)

    def level_up(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> "GameState":
        """Perform the level up action: put level counters.

        Args:
            game_state: Current game state.
            permanent: The creature to level up.

        Returns:
            Modified game state with level counters added.
        """
        # Parse counter amount from effect text
        counter_count = self._parse_counter_count()

        counters = dict(permanent.counters or {})
        counters["level"] = counters.get("level", 0) + counter_count
        permanent.counters = counters

        logger.info(
            "Leveled up %s to level %d",
            permanent.card.name,
            counters["level"],
        )
        return game_state

    def get_active_abilities(self, permanent: "Permanent") -> list[str]:
        """Get all level abilities that are currently active.

        Args:
            permanent: The leveled creature.

        Returns:
            List of ability texts for all levels currently met.
        """
        current_level = self.get_level(permanent)
        active = []
        for level, ability in self.level_abilities:
            if current_level >= level:
                active.append(ability)
        return active

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply the level up effect."""
        return self.level_up(game_state, permanent)

    def _parse_counter_count(self) -> int:
        """Parse the number of counters to add from the effect text."""
        match = re.search(r"put\s+(\d+)\s+\+1/\+1\s+counter", self.effect, re.IGNORECASE)
        if match:
            return int(match.group(1))
        match = re.search(r"put\s+a\s+\+1/\+1\s+counter", self.effect, re.IGNORECASE)
        if match:
            return 1
        return 2  # Default for level up is 2 counters

    def get_trigger_description(self) -> str:
        return f"Level Up {self.cost}: {self.effect}"


def parse_level_up(oracle_text: str) -> LevelUpKeyword | None:
    """Parse Level Up keyword from oracle text.

    Args:
        oracle_text: The card's oracle text.

    Returns:
        LevelUpKeyword if found, None otherwise.
    """
    cost_match = _LEVEL_UP_PATTERN.search(oracle_text)
    if not cost_match:
        return None

    cost = cost_match.group(1).replace(" ", "")
    effect = cost_match.group(2)

    # Parse level N abilities
    level_abilities: list[tuple[int, str]] = []
    for match in _LEVEL_N_PATTERN.finditer(oracle_text):
        level = int(match.group(1))
        ability = match.group(2)
        level_abilities.append((level, ability))

    return LevelUpKeyword(cost=cost, effect=effect, level_abilities=level_abilities)
