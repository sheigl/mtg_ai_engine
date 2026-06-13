"""Flashback keyword (CR 702.34).

Flashback gives an alternate way to cast a spell from the graveyard.
Pay the flashback cost, then exile the card instead of putting it
anywhere else.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_FLASHBACK_PATTERN = re.compile(
    r"flashback\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE
)
_FLASHBACK_PLAIN = re.compile(r"\bflashback\b", re.IGNORECASE)


class Flashback(CostKeyword):
    name = "flashback"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("flashback" in k.lower() for k in keywords)
            or bool(_FLASHBACK_PLAIN.search(oracle))
        )

    @staticmethod
    def has_flashback(keywords: list[str]) -> bool:
        return any("flashback" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_FLASHBACK_PLAIN.search(oracle_text))

    @staticmethod
    def parse_flashback_cost(oracle_text: str) -> str | None:
        match = _FLASHBACK_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Flashback | None:
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_flashback_cost(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
