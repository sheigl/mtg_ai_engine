"""Crew keyword (CR 702.147).

Crew N means "Tap any number of untapped creatures you control with
total power N or more: This permanent becomes an artifact creature until
end of turn."
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import KeywordAbility

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_CREW_PATTERN = re.compile(r"crew\s+(\d+)", re.IGNORECASE)


class Crew(KeywordAbility):
    name = "crew"

    def __init__(self, value: int = 1):
        self.value = value

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("crew" in k.lower() for k in keywords)
            or bool(_CREW_PATTERN.search(oracle))
        )

    @staticmethod
    def has_crew(keywords: list[str]) -> bool:
        return any("crew" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_CREW_PATTERN.search(oracle_text))

    @staticmethod
    def parse_crew_value(oracle_text: str) -> int:
        match = _CREW_PATTERN.search(oracle_text or "")
        if match:
            return int(match.group(1))
        return 1

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Crew | None:
        if cls.from_oracle_text(oracle_text):
            return cls(value=cls.parse_crew_value(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
