"""Madness keyword (CR 702.35).

Madness {cost} is a replacement effect that applies when a player would
discard a card with madness. Instead of being put into the graveyard,
it's exiled and may be cast for its madness cost.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_MADNESS_PATTERN = re.compile(
    r"madness\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE
)
_MADNESS_PLAIN = re.compile(r"\bmadness\b", re.IGNORECASE)


class Madness(CostKeyword):
    name = "madness"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("madness" in k.lower() for k in keywords)
            or bool(_MADNESS_PLAIN.search(oracle))
        )

    @staticmethod
    def has_madness(keywords: list[str]) -> bool:
        return any("madness" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_MADNESS_PLAIN.search(oracle_text))

    @staticmethod
    def parse_madness_cost(oracle_text: str) -> str | None:
        match = _MADNESS_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Madness | None:
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_madness_cost(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
