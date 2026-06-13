"""Escape keyword (CR 702.149).

Escape {cost} — {cost}, Exile N other cards from your graveyard:
Cast this card from your graveyard. If you cast it this way, it
exiles on leaving the battlefield.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_ESCAPE_COST_PATTERN = re.compile(
    r"escape\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE
)
_ESCAPE_EXILE_PATTERN = re.compile(r"exile\s+(\w+)\s+other", re.IGNORECASE)
_ESCAPE_PLAIN = re.compile(r"\bescape\b", re.IGNORECASE)


class Escape(CostKeyword):
    name = "escape"

    def __init__(self, cost: str | None = None, exile_count: int = 0):
        self.cost = cost
        self.exile_count = exile_count

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("escape" in k.lower() for k in keywords)
            or bool(_ESCAPE_PLAIN.search(oracle))
        )

    @staticmethod
    def has_escape(keywords: list[str]) -> bool:
        return any("escape" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_ESCAPE_PLAIN.search(oracle_text))

    @staticmethod
    def parse_escape_cost(oracle_text: str) -> str | None:
        match = _ESCAPE_COST_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def parse_exile_count(oracle_text: str) -> int:
        match = _ESCAPE_EXILE_PATTERN.search(oracle_text or "")
        if match:
            word = match.group(1).lower()
            number_map = {
                "one": 1, "two": 2, "three": 3, "four": 4,
                "five": 5, "six": 6, "seven": 7, "eight": 8,
                "nine": 9, "ten": 10,
            }
            return number_map.get(word, 1)
        return 0

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Escape | None:
        if cls.from_oracle_text(oracle_text):
            return cls(
                cost=cls.parse_escape_cost(oracle_text),
                exile_count=cls.parse_exile_count(oracle_text),
            )
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
