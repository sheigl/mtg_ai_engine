"""Storm keyword (CR 702.52).

Storm is a triggered ability that copies the spell for each other spell
cast before it this turn.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_STORM_PATTERN = re.compile(r"\bstorm\b", re.IGNORECASE)


class Storm(TriggeredKeyword):
    name = "storm"

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("storm" in k.lower() for k in keywords)
            or bool(_STORM_PATTERN.search(oracle))
        )

    @staticmethod
    def has_storm(keywords: list[str]) -> bool:
        return "storm" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_STORM_PATTERN.search(oracle_text))

    @staticmethod
    def get_storm_count(game_state: GameState) -> int:
        return getattr(game_state, "spells_cast_this_turn", 0)

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        return game_state
