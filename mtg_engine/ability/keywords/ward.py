"""Ward keyword (CR 702.145).

Ward is a triggered ability that counters a spell or ability unless its
controller pays an additional cost. Ward {2} means "Whenever this
permanent becomes the target of a spell or ability, counter it unless
that spell or ability's controller pays {2}."
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_WARD_PATTERN = re.compile(r"ward\s*[—\-]?\s*(?:pay\s+)?(\{(?:[^}]+}\s*)+)", re.IGNORECASE)
_WARD_COST_PATTERN = re.compile(r"ward\s+(\d+)", re.IGNORECASE)
_WARD_DASH_EVERYTHING = re.compile(r"ward\s*[—\-]\s*", re.IGNORECASE)


class Ward(TriggeredKeyword):
    name = "ward"

    def __init__(self, cost: str = "{2}"):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("ward" in k.lower() for k in keywords)
            or bool(_WARD_PATTERN.search(oracle))
            or bool(_WARD_COST_PATTERN.search(oracle))
        )

    @staticmethod
    def has_ward(keywords: list[str]) -> bool:
        return any("ward" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_WARD_PATTERN.search(oracle_text)) or bool(_WARD_COST_PATTERN.search(oracle_text))

    @staticmethod
    def parse_ward_cost(oracle_text: str) -> str:
        match = _WARD_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        match = _WARD_COST_PATTERN.search(oracle_text or "")
        if match:
            n = int(match.group(1))
            return "{" + str(n) + "}"
        return "{2}"

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Ward | None:
        if cls.from_oracle_text(oracle_text):
            cost = cls.parse_ward_cost(oracle_text)
            return cls(cost=cost)
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
