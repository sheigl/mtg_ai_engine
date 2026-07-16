"""Equip keyword (CR 702.5).

Equip {cost} means "Activate this ability only any time you could cast a
sorcery: Attach this Equipment to target creature you control. Play this
ability only any time you could cast a sorcery."
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_EQUIP_PATTERN = re.compile(
    r"equip\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE
)
_EQUIP_PLAIN = re.compile(r"\bequip\b", re.IGNORECASE)


class Equip(CostKeyword):
    name = "equip"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("equip" in k.lower() for k in keywords)
            or bool(_EQUIP_PLAIN.search(oracle))
        )

    @staticmethod
    def has_equip(keywords: list[str]) -> bool:
        return any("equip" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_EQUIP_PLAIN.search(oracle_text))

    @staticmethod
    def parse_equip_cost(oracle_text: str) -> str | None:
        match = _EQUIP_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Equip | None:
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_equip_cost(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
