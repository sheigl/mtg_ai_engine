"""Cascade keyword (CR 702.87).

Cascade is a triggered ability that exiles cards from the top of the
library until a nonland card with lesser mana value is found, then
allows casting it without paying its mana cost.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_CASCADE_PATTERN = re.compile(r"\bcascade\b", re.IGNORECASE)


class Cascade(TriggeredKeyword):
    name = "cascade"

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("cascade" in k.lower() for k in keywords)
            or bool(_CASCADE_PATTERN.search(oracle))
        )

    @staticmethod
    def has_cascade(keywords: list[str]) -> bool:
        return "cascade" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_CASCADE_PATTERN.search(oracle_text))

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
