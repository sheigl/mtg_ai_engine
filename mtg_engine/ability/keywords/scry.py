"""Scry keyword action (CR 701.20).

Scry N means look at the top N cards of your library, then put any number
of them on the bottom of your library and the rest on top in any order.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import KeywordAbility

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_SCRY_PATTERN = re.compile(r"scry\s+(\d+)", re.IGNORECASE)


class Scry(KeywordAbility):
    name = "scry"

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        return any("scry" in k.lower() for k in keywords)

    @staticmethod
    def has_scry(keywords: list[str]) -> bool:
        return any("scry" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_SCRY_PATTERN.search(oracle_text))

    @staticmethod
    def parse_scry_value(oracle_text: str) -> int:
        match = _SCRY_PATTERN.search(oracle_text or "")
        if match:
            return int(match.group(1))
        return 1

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
