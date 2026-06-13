"""Delve keyword (CR 702.80).

Delve allows exiling cards from your graveyard to help pay for a spell's
mana cost. Each card exiled reduces the total cost by {1}.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_DELVE_PATTERN = re.compile(r"\bdelve\b", re.IGNORECASE)


class Delve(CostKeyword):
    name = "delve"

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("delve" in k.lower() for k in keywords)
            or bool(_DELVE_PATTERN.search(oracle))
        )

    @staticmethod
    def has_delve(keywords: list[str]) -> bool:
        return "delve" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_DELVE_PATTERN.search(oracle_text))

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
