"""Ninjutsu keyword (CR 702.61).

Ninjutsu {cost} is an activated ability that lets an unblocked attacking
creature be returned to its owner's hand, and this card enters the
battlefield tapped and attacking.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_NINJUTSU_PATTERN = re.compile(
    r"ninjutsu\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE
)
_NINJUTSU_PLAIN = re.compile(r"\bninjutsu\b", re.IGNORECASE)


class Ninjutsu(CostKeyword):
    name = "ninjutsu"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("ninjutsu" in k.lower() for k in keywords)
            or bool(_NINJUTSU_PLAIN.search(oracle))
        )

    @staticmethod
    def has_ninjutsu(keywords: list[str]) -> bool:
        return any("ninjutsu" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_NINJUTSU_PLAIN.search(oracle_text))

    @staticmethod
    def parse_ninjutsu_cost(oracle_text: str) -> str | None:
        match = _NINJUTSU_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Ninjutsu | None:
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_ninjutsu_cost(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
