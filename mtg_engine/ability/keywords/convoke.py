"""Convoke keyword (CR 702.77).

Convoke allows tapping creatures to help pay for a spell's mana cost.
Each creature tapped while casting reduces the total cost by {1} or one
mana of that creature's color.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_CONVOKE_PATTERN = re.compile(r"\bconvoke\b", re.IGNORECASE)


class Convoke(CostKeyword):
    name = "convoke"

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("convoke" in k.lower() for k in keywords)
            or bool(_CONVOKE_PATTERN.search(oracle))
        )

    @staticmethod
    def has_convoke(keywords: list[str]) -> bool:
        return "convoke" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_CONVOKE_PATTERN.search(oracle_text))

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
