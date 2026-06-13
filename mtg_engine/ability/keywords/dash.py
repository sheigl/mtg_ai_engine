"""Dash keyword (CR 702.138).

Dash {cost} is an alternative cost to cast a creature spell. If paid,
the creature gains haste and is returned to its owner's hand at the
beginning of the next end step.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_DASH_PATTERN = re.compile(
    r"dash\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE
)
_DASH_PLAIN = re.compile(r"\bdash\b", re.IGNORECASE)


class Dash(CostKeyword):
    name = "dash"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("dash" in k.lower() for k in keywords)
            or bool(_DASH_PLAIN.search(oracle))
        )

    @staticmethod
    def has_dash(keywords: list[str]) -> bool:
        return any("dash" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_DASH_PLAIN.search(oracle_text))

    @staticmethod
    def parse_dash_cost(oracle_text: str) -> str | None:
        match = _DASH_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Dash | None:
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_dash_cost(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
