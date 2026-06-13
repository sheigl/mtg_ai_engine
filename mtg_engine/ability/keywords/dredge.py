"""Dredge keyword (CR 702.60).

Dredge N replaces a card draw: you may put N cards from your graveyard
into your library instead of drawing a card. If you do, return this card
from your graveyard to your hand.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import KeywordAbility

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_DREDGE_PATTERN = re.compile(r"dredge\s+(\d+)", re.IGNORECASE)


class Dredge(KeywordAbility):
    name = "dredge"

    def __init__(self, value: int = 1):
        self.value = value

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("dredge" in k.lower() for k in keywords)
            or bool(_DREDGE_PATTERN.search(oracle))
        )

    @staticmethod
    def has_dredge(keywords: list[str]) -> bool:
        return any("dredge" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_DREDGE_PATTERN.search(oracle_text))

    @staticmethod
    def parse_dredge_value(oracle_text: str) -> int:
        match = _DREDGE_PATTERN.search(oracle_text or "")
        if match:
            return int(match.group(1))
        return 1

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Dredge | None:
        if cls.from_oracle_text(oracle_text):
            return cls(value=cls.parse_dredge_value(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
