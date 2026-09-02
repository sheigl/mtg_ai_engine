import re
import logging
from typing import TYPE_CHECKING
from pydantic import BaseModel

from mtg_engine.ability.keywords.base import CostKeyword

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_OVERLOAD_PATTERN = re.compile(r"\bOverload\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_OVERLOAD_PLAIN = re.compile(r"\bOverload\b", re.IGNORECASE)


class OverloadModel(BaseModel):
    name: str = ""
    overload_cost: str | None = None
    type_line: str = ""
    oracle_text: str = ""
    overload_paid: bool = False

    @staticmethod
    def from_oracle_text(name: str, oracle_text: str, type_line: str) -> "OverloadModel":
        overload_cost = parse_overload_cost(oracle_text)
        return OverloadModel(
            name=name,
            overload_cost=overload_cost,
            type_line=type_line,
            oracle_text=oracle_text,
        )

    @property
    def is_overloaded(self) -> bool:
        return self.overload_paid and self.overload_cost is not None


def parse_overload_cost(oracle_text: str) -> str | None:
    """Extract the overload cost from oracle text.

    Handles: 'Overload {3}', 'Overload {2}{R}'
    Returns None if no overload keyword.
    """
    if not oracle_text:
        return None
    m = _OVERLOAD_PATTERN.search(oracle_text)
    if m:
        return m.group("cost").strip()
    return None


def has_overload(oracle_text: str) -> bool:
    """Check if a card has the overload keyword."""
    if not oracle_text:
        return False
    return bool(_OVERLOAD_PLAIN.search(oracle_text))


class OverloadKeyword(CostKeyword):
    name = "overload"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    def applies(self, game_state: "GameState", permanent: "Permanent") -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("overload" in k.lower() for k in keywords)
        has_oracle = bool(_OVERLOAD_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_overload_keywords(keywords: list[str]) -> bool:
        return any("overload" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_OVERLOAD_PLAIN.search(oracle_text))

    @staticmethod
    def parse_overload_cost_static(oracle_text: str) -> str | None:
        return parse_overload_cost(oracle_text)

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "OverloadKeyword | None":
        if cls.from_oracle_text(oracle_text):
            return cls(cost=parse_overload_cost(oracle_text))
        return None

    def apply(self, game_state: "GameState", permanent: "Permanent", target: "Permanent | None" = None) -> "GameState":
        """Apply overload (CR 702.95).

        Overload {cost} is an ALTERNATIVE cost. If paid, the spell's text is changed
        by replacing all instances of "target" with "each". The spell targets nothing.

        - Human caster: queues pending_overload_choice (resolved=False). Cast deferred.
        - AI caster: auto-resolves by affordability. If overload cost affordable,
          pay overload; else pay base cost.
        - No-op guards: no overload cost parseable → return SAME object.
        """
        from mtg_engine.engine.mana import can_pay_cost
        from mtg_engine.engine.zones import get_player

        card = permanent.card
        oracle_text = card.oracle_text or ""

        # No-op guard 1: must have overload
        if not (self.has_overload_keywords(card.keywords or []) or bool(_OVERLOAD_PLAIN.search(oracle_text))):
            return game_state

        # No-op guard 2: parseable cost required
        overload_cost = parse_overload_cost(oracle_text)
        if not overload_cost:
            return game_state

        controller = permanent.controller

        is_human = (
            getattr(game_state, "human_player_name", None) is not None
            and controller == game_state.human_player_name
        )

        if is_human:
            game_state = game_state.model_copy(update={
                "pending_overload_choice": {
                    "player": controller,
                    "card_id": card.id,
                    "card_name": card.name,
                    "overload_cost": overload_cost,
                    "base_cost": card.mana_cost or "",
                    "resolved": False,
                    "paid": False,
                }
            })
            logger.info(
                "%s: queued overload choice for %s (overload cost: %s, base: %s)",
                controller, card.name, overload_cost, card.mana_cost or ""
            )
            return game_state

        # AI auto-resolution
        player = get_player(game_state, controller)
        if player is None:
            logger.warning("Player not found for overload resolution: %s", controller)
            return game_state

        # Heuristic: pay overload if affordable
        can_pay = can_pay_cost(player.mana_pool, overload_cost)
        paid = bool(can_pay)

        game_state = game_state.model_copy(update={
            "pending_overload_choice": {
                "player": controller,
                "card_id": card.id,
                "card_name": card.name,
                "overload_cost": overload_cost,
                "base_cost": card.mana_cost or "",
                "resolved": True,
                "paid": paid,
            }
        })
        logger.info(
            "%s: AI resolved overload for %s (overload cost: %s, paid: %s)",
            controller, card.name, overload_cost, paid
        )
        return game_state


def get_overload_targets(oracle_text: str, game_state) -> list[str]:
    """Get all valid targets for an overloaded spell.

    For overloaded spells, target ALL appropriate permanents/players instead of just one.
    """
    if not oracle_text:
        return []

    targets = []
    oracle_lower = oracle_text.lower()

    if "destroy target creature" in oracle_lower or "destroy all creatures" in oracle_lower:
        targets = [p.id for p in game_state.battlefield if "creature" in p.card.type_line.lower()]

    elif "target opponent" in oracle_lower:
        for player in game_state.players:
            if player.name != game_state.active_player:
                targets.append(player.name)

    elif "target permanent" in oracle_lower:
        targets = [p.id for p in game_state.battlefield]

    return targets
