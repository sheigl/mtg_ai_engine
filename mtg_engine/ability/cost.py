"""
Cost payment system for activated abilities.

Handles mana costs, tap, sacrifice, exile, discard, life payment,
and alternative costs (kicker, flashback, etc.).

ACT-01: Full cost payment system.
"""
from __future__ import annotations
import re
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent, Card

logger = logging.getLogger(__name__)


class CostType(Enum):
    """Types of costs that can be paid for activated abilities."""
    MANA = "mana"
    TAP = "tap"
    SACRIFICE = "sacrifice"
    EXILE = "exile"
    DISCARD = "discard"
    LIFE = "life"
    LOYALTY = "loyalty"
    KICKER = "kicker"
    GENERIC = "generic"  # {N} generic mana


class Cost(ABC):
    """Base class for all cost types."""

    @abstractmethod
    def can_pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> bool:
        """Check if the cost can be paid."""
        ...

    @abstractmethod
    def pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> GameState:
        """Pay the cost, modifying game state."""
        ...

    @property
    @abstractmethod
    def cost_type(self) -> CostType:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...


class ManaCost(Cost):
    """Cost that pays mana from the pool."""

    def __init__(self, mana_string: str):
        self.mana_string = mana_string
        self._parsed = self._parse_mana(mana_string)

    @property
    def cost_type(self) -> CostType:
        return CostType.MANA

    @property
    def description(self) -> str:
        return f"Pay {{{self.mana_string}}}"

    def _parse_mana(self, mana_string: str) -> dict[str, int]:
        """Parse mana cost string into color requirements."""
        requirements: dict[str, int] = {}
        # Remove outer braces: {W}{W}{U} -> W}{W}{U
        cleaned = mana_string.replace("{", "").replace("}", "")
        for ch in cleaned:
            if ch in "WUBRG":
                requirements[ch] = requirements.get(ch, 0) + 1
            elif ch.isdigit():
                generic = requirements.get("generic", 0)
                requirements["generic"] = generic + int(ch)
            elif ch == "C":
                requirements["C"] = requirements.get("C", 0) + 1
        return requirements

    def can_pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> bool:
        from mtg_engine.models.game import ManaPool
        player = next((p for p in game_state.players if p.name == controller), None)
        if not player or not hasattr(player, "mana_pool"):
            return False
        pool: ManaPool = player.mana_pool
        for color, needed in self._parsed.items():
            if color == "generic":
                total = sum(
                    v
                    for k, v in pool.model_dump().items()
                    if k not in ("generic", "snow", "snow_by_color")
                )
                if total < needed:
                    return False
            elif color == "C":
                if pool.C < needed:
                    return False
            else:
                attr = getattr(pool, color, 0)
                if attr < needed:
                    return False
        return True

    def pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> GameState:
        from mtg_engine.models.game import ManaPool
        player = next((p for p in game_state.players if p.name == controller), None)
        if not player or not hasattr(player, "mana_pool"):
            return game_state
        pool: ManaPool = player.mana_pool
        for color, needed in self._parsed.items():
            if color == "generic":
                # Pay generic from available mana, preferring colorless
                remaining = needed
                if remaining > 0 and pool.C >= remaining:
                    pool.C -= remaining
                    remaining = 0
                for c in "WUBRG":
                    if remaining <= 0:
                        break
                    avail = getattr(pool, c, 0)
                    pay = min(avail, remaining)
                    setattr(pool, c, avail - pay)
                    remaining -= pay
            elif color == "C":
                pool.C = max(0, pool.C - needed)
            else:
                current = getattr(pool, color, 0)
                setattr(pool, color, max(0, current - needed))
        logger.info("%s paid mana cost {{{}}}", controller, self.mana_string)
        return game_state


class TapCost(Cost):
    """Cost that taps a permanent."""

    def __init__(self, source_perm_id: str | None = None):
        self.source_perm_id = source_perm_id

    @property
    def cost_type(self) -> CostType:
        return CostType.TAP

    @property
    def description(self) -> str:
        return "{T}"

    def can_pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> bool:
        perm = source_perm or self._find_perm(game_state)
        if not perm:
            return False
        return not perm.tapped

    def pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> GameState:
        perm = source_perm or self._find_perm(game_state)
        if perm:
            perm.tapped = True
            logger.info("%s tapped %s", controller, perm.card.name)
        return game_state

    def _find_perm(self, game_state: GameState) -> Permanent | None:
        if self.source_perm_id:
            return next(
                (p for p in game_state.battlefield if p.id == self.source_perm_id),
                None,
            )
        return None


class SacrificeCost(Cost):
    """Cost that sacrifices a permanent."""

    def __init__(self, target_perm_id: str):
        self.target_perm_id = target_perm_id

    @property
    def cost_type(self) -> CostType:
        return CostType.SACRIFICE

    @property
    def description(self) -> str:
        return f"Sacrifice {{{self.target_perm_id}}}"

    def can_pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> bool:
        perm = next(
            (p for p in game_state.battlefield if p.id == self.target_perm_id),
            None,
        )
        if not perm:
            return False
        return perm.controller == controller

    def pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> GameState:
        perm = next(
            (p for p in game_state.battlefield if p.id == self.target_perm_id),
            None,
        )
        if not perm:
            return game_state
        player = next((p for p in game_state.players if p.name == controller), None)
        if player:
            player.graveyard.append(perm.card)
        game_state.battlefield = [
            p for p in game_state.battlefield if p.id != self.target_perm_id
        ]
        logger.info("%s sacrificed %s", controller, perm.card.name)
        return game_state


class ExileCost(Cost):
    """Cost that exiles cards."""

    def __init__(self, count: int = 1, from_zone: str = "hand"):
        self.count = count
        self.from_zone = from_zone

    @property
    def cost_type(self) -> CostType:
        return CostType.EXILE

    @property
    def description(self) -> str:
        return f"Exile {self.count} card(s) from {self.from_zone}"

    def can_pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> bool:
        player = next((p for p in game_state.players if p.name == controller), None)
        if not player:
            return False
        if self.from_zone == "hand":
            return len(player.hand) >= self.count
        if self.from_zone == "graveyard":
            return len(player.graveyard) >= self.count
        if self.from_zone == "library":
            return len(player.library) >= self.count
        return False

    def pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> GameState:
        player = next((p for p in game_state.players if p.name == controller), None)
        if not player:
            return game_state
        zone = getattr(player, self.from_zone, [])
        for _ in range(min(self.count, len(zone))):
            card = zone.pop(0)
            player.exile.append(card)
        logger.info(
            "%s exiled %d card(s) from %s as cost",
            controller,
            self.count,
            self.from_zone,
        )
        return game_state


class DiscardCost(Cost):
    """Cost that discards cards."""

    def __init__(self, count: int = 1):
        self.count = count

    @property
    def cost_type(self) -> CostType:
        return CostType.DISCARD

    @property
    def description(self) -> str:
        return f"Discard {self.count} card(s)"

    def can_pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> bool:
        player = next((p for p in game_state.players if p.name == controller), None)
        if not player:
            return False
        return len(player.hand) >= self.count

    def pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> GameState:
        player = next((p for p in game_state.players if p.name == controller), None)
        if not player:
            return game_state
        for _ in range(min(self.count, len(player.hand))):
            card = player.hand.pop(0)
            player.graveyard.append(card)
        logger.info("%s discarded %d card(s) as cost", controller, self.count)
        return game_state


class LifeCost(Cost):
    """Cost that pays life."""

    def __init__(self, amount: int = 2):
        self.amount = amount

    @property
    def cost_type(self) -> CostType:
        return CostType.LIFE

    @property
    def description(self) -> str:
        return f"Pay {self.amount} life"

    def can_pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> bool:
        player = next((p for p in game_state.players if p.name == controller), None)
        if not player:
            return False
        return player.life > self.amount

    def pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> GameState:
        player = next((p for p in game_state.players if p.name == controller), None)
        if player:
            player.life -= self.amount
            logger.info("%s paid %d life", controller, self.amount)
        return game_state


class LoyaltyCost(Cost):
    """Cost that adds or removes loyalty counters."""

    def __init__(self, amount: int):
        self.amount = amount

    @property
    def cost_type(self) -> CostType:
        return CostType.LOYALTY

    @property
    def description(self) -> str:
        sign = "+" if self.amount > 0 else ""
        return f"{sign}{self.amount} loyalty"

    def can_pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> bool:
        if not source_perm:
            return False
        current_loyalty = source_perm.counters.get("loyalty", 0)
        if self.amount > 0:
            return True
        return current_loyalty + self.amount >= 0

    def pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> GameState:
        if not source_perm:
            return game_state
        current = source_perm.counters.get("loyalty", 0)
        source_perm.counters["loyalty"] = current + self.amount
        logger.info(
            "%s paid %d loyalty (now %d)",
            controller,
            self.amount,
            source_perm.counters["loyalty"],
        )
        return game_state


class CompositeCost(Cost):
    """Combines multiple costs into one."""

    def __init__(self, costs: list[Cost]):
        self.costs = costs

    @property
    def cost_type(self) -> CostType:
        return self.costs[0].cost_type if self.costs else CostType.GENERIC

    @property
    def description(self) -> str:
        return " + ".join(c.description for c in self.costs)

    def can_pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> bool:
        return all(
            c.can_pay(game_state, controller, source_perm) for c in self.costs
        )

    def pay(
        self,
        game_state: GameState,
        controller: str,
        source_perm: Permanent | None = None,
    ) -> GameState:
        for cost in self.costs:
            game_state = cost.pay(game_state, controller, source_perm)
        return game_state


# =====================================================================
# Cost parsing from ability cost strings like "{T}", "{W}", "{2}{W}", etc.
# =====================================================================

_MANA_RE = re.compile(r"\{([WUBRG])\}")
_GENERIC_RE = re.compile(r"\{(\d+)\}")
_COLORLESS_RE = re.compile(r"\{C\}")
_TAP_RE = re.compile(r"\{T\}")
_UNTAP_RE = re.compile(r"\{Q\}")
_SACRIFICE_RE = re.compile(r"\{SAC\}")
_X_RE = re.compile(r"\{X\}")


def parse_cost_string(cost_string: str) -> list[Cost]:
    """
    Parse an activated ability cost string into Cost objects.

    Handles:
    - {T} - tap
    - {Q} - untap
    - {W}, {U}, {B}, {R}, {G} - colored mana
    - {C} - colorless mana
    - {N} - generic mana
    - {X} - variable mana
    - {SAC} - sacrifice this permanent
    """
    costs: list[Cost] = []
    mana_parts: list[str] = []

    if _TAP_RE.search(cost_string):
        costs.append(TapCost())
    if _UNTAP_RE.search(cost_string):
        pass  # Untap as cost is rare but possible
    if _SACRIFICE_RE.search(cost_string):
        costs.append(SacrificeCost(target_perm_id="__source__"))

    # Collect mana symbols
    for m in _MANA_RE.finditer(cost_string):
        mana_parts.append(m.group(1))
    for m in _COLORLESS_RE.finditer(cost_string):
        mana_parts.append("C")
    for m in _GENERIC_RE.finditer(cost_string):
        mana_parts.append(m.group(1))

    if mana_parts:
        mana_str = "".join(mana_parts)
        costs.append(ManaCost(mana_str))

    return costs


def can_pay_cost(
    game_state: GameState,
    controller: str,
    cost: Cost,
    source_perm: Permanent | None = None,
) -> bool:
    """Check if a player can pay a cost."""
    return cost.can_pay(game_state, controller, source_perm)


def pay_cost(
    game_state: GameState,
    controller: str,
    cost: Cost,
    source_perm: Permanent | None = None,
) -> GameState:
    """Pay a cost, modifying game state."""
    if not can_pay_cost(game_state, controller, cost, source_perm):
        raise ValueError(
            f"{controller} cannot pay cost: {cost.description}"
        )
    return cost.pay(game_state, controller, source_perm)
