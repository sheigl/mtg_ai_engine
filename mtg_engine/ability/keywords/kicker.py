"""Kicker keyword (CR 702.33).

Kicker is an additional cost that may be paid as the spell is cast.
Alternative kicker costs may specify different mana or non-mana payments.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_KICKER_PATTERN = re.compile(r"kicker\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE)
_KICKER_PLAIN = re.compile(r"\bkicker\b", re.IGNORECASE)


class Kicker(CostKeyword):
    name = "kicker"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("kicker" in k.lower() for k in keywords)
            or bool(_KICKER_PLAIN.search(oracle))
        )

    @staticmethod
    def has_kicker(keywords: list[str]) -> bool:
        return any("kicker" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_KICKER_PLAIN.search(oracle_text))

    @staticmethod
    def parse_kicker_cost(oracle_text: str) -> str | None:
        match = _KICKER_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Kicker | None:
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_kicker_cost(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
