"""
Counter keyword abilities.

KW-04: Implements counter placement and removal keywords including
+1/+1 counters, -1/-1 counters, and their interactions.
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import KeywordAbility

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Card, Permanent

logger = logging.getLogger(__name__)

# Counter patterns in oracle text
_COUNTER_PATTERNS = [
    re.compile(r"put a \+1/\+1 counter on (?:this|~)", re.IGNORECASE),
    re.compile(r"put (\d+) \+1/\+1 counters? on (?:this|~)", re.IGNORECASE),
    re.compile(r"put a -1/-1 counter on (?:this|~)", re.IGNORECASE),
    re.compile(r"put (\d+) -1/-1 counters? on (?:this|~)", re.IGNORECASE),
    re.compile(r"remove a \+1/\+1 counter from (?:this|~)", re.IGNORECASE),
    re.compile(r"remove all counters? from (?:this|~)", re.IGNORECASE),
]


class CounterKeyword(KeywordAbility):
    """Base class for counter-related keyword abilities.

    Handles counter placement, removal, and counter-based calculations.
    """

    name = "counter"
    counter_type: str = "+1/+1"

    def __init__(self, counter_type: str = "+1/+1", count: int = 1):
        """Initialize counter keyword.

        Args:
            counter_type: Type of counter ("+1/+1", "-1/-1", "charge", etc.).
            count: Number of counters to place/remove.
        """
        self.counter_type = counter_type
        self.count = count

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this permanent has counter-related abilities."""
        oracle = permanent.card.oracle_text or ""
        return any(pattern.search(oracle) for pattern in _COUNTER_PATTERNS)

    def get_counter_count(
        self,
        permanent: "Permanent",
        counter_type: str | None = None,
    ) -> int:
        """Get the number of counters of a given type on a permanent."""
        counters = permanent.counters or {}
        ctype = counter_type or self.counter_type
        return counters.get(ctype, 0)

    def add_counters(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        counter_type: str | None = None,
        count: int | None = None,
    ) -> "GameState":
        """Add counters to a permanent.

        Args:
            game_state: Current game state.
            permanent: Permanent to add counters to.
            counter_type: Type of counter to add.
            count: Number of counters to add.

        Returns:
            Modified game state.
        """
        ctype = counter_type or self.counter_type
        cnt = count or self.count
        counters = dict(permanent.counters or {})
        counters[ctype] = counters.get(ctype, 0) + cnt
        permanent.counters = counters
        logger.info(
            "Added %d %s counter(s) to %s",
            cnt,
            ctype,
            permanent.card.name,
        )
        return game_state

    def remove_counters(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        counter_type: str | None = None,
        count: int | None = None,
    ) -> "GameState":
        """Remove counters from a permanent.

        Args:
            game_state: Current game state.
            permanent: Permanent to remove counters from.
            counter_type: Type of counter to remove.
            count: Number of counters to remove.

        Returns:
            Modified game state.
        """
        ctype = counter_type or self.counter_type
        cnt = count or self.count
        counters = dict(permanent.counters or {})
        current = counters.get(ctype, 0)
        counters[ctype] = max(0, current - cnt)
        permanent.counters = counters
        logger.info(
            "Removed %d %s counter(s) from %s",
            cnt,
            ctype,
            permanent.card.name,
        )
        return game_state

    def remove_all_counters(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> "GameState":
        """Remove all counters from a permanent."""
        permanent.counters = {}
        logger.info("Removed all counters from %s", permanent.card.name)
        return game_state

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply counter effect by default adds counters."""
        target_perm = target or permanent
        return self.add_counters(game_state, target_perm)

    def get_trigger_description(self) -> str:
        return f"Put {self.count} {self.counter_type} counter(s)"


class PlusOnePlusOneCounter(CounterKeyword):
    """+1/+1 counter placement and tracking.

    CR 704.5m: If +1/+1 and -1/-1 counters are on the same permanent,
    they cancel each other out in groups of two.
    """

    name = "plus_one_plus_one"
    counter_type = "+1/+1"

    def __init__(self, count: int = 1):
        super().__init__(counter_type="+1/+1", count=count)

    def get_pt_modification(self, permanent: "Permanent") -> tuple[int, int]:
        """Get the P/T modification from +1/+1 counters."""
        count = self.get_counter_count(permanent, "+1/+1")
        minus_count = self.get_counter_count(permanent, "-1/-1")
        # CR 704.5m: Canceling
        net_plus = max(0, count - minus_count)
        return (net_plus, net_plus)


class MinusOneMinusOneCounter(CounterKeyword):
    """-1/-1 counter placement and tracking.

    CR 704.5m: If +1/+1 and -1/-1 counters are on the same permanent,
    they cancel each other out in groups of two.
    """

    name = "minus_one_minus_one"
    counter_type = "-1/-1"

    def __init__(self, count: int = 1):
        super().__init__(counter_type="-1/-1", count=count)

    def get_pt_modification(self, permanent: "Permanent") -> tuple[int, int]:
        """Get the P/T modification from -1/-1 counters."""
        count = self.get_counter_count(permanent, "-1/-1")
        plus_count = self.get_counter_count(permanent, "+1/+1")
        # CR 704.5m: Canceling
        net_minus = max(0, count - plus_count)
        return (-net_minus, -net_minus)

    def check_destruction(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if -1/-1 counters dealt lethal damage.

        CR 704.5h: If a permanent has damage marked on it and -1/-1 counters,
        check state-based actions for destruction.
        """
        plus_count = self.get_counter_count(permanent, "+1/+1")
        minus_count = self.get_counter_count(permanent, "-1/-1")
        net_minus = max(0, minus_count - plus_count)

        # Get base toughness
        toughness_str = permanent.card.toughness or "1"
        try:
            base_toughness = int(toughness_str)
        except ValueError:
            base_toughness = 1

        # Apply bonuses
        effective_toughness = base_toughness + permanent.toughness_bonus - net_minus
        total_damage = permanent.damage_marked

        return total_damage >= effective_toughness and effective_toughness > 0


class ChargeCounter(CounterKeyword):
    """Charge counter for artifacts (Modular keyword support)."""

    name = "charge"
    counter_type = "charge"

    def __init__(self, count: int = 1):
        super().__init__(counter_type="charge", count=count)


class TimeCounter(CounterKeyword):
    """Time counter for Vanishing keyword."""

    name = "time"
    counter_type = "time"

    def __init__(self, count: int = 1):
        super().__init__(counter_type="time", count=count)
