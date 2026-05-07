"""
Flanking keyword ability.

CMB-04: Implements the Flanking mechanic.
CR 702.64: Flanking is a static ability that triggers when a creature
with flanking is declared as a blocker. If the blocked creature doesn't
have flanking, it gets -1/-1 until end of turn.

Example: "Flanking" — Whenever this creature blocks a creature without
flanking, that creature gets -1/-1 until end of turn.
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Card, Permanent

logger = logging.getLogger(__name__)

# Flanking pattern
_FLANKING_PATTERN = re.compile(r"\bflanking\b", re.IGNORECASE)


class FlankingKeyword(TriggeredKeyword):
    """Flanking keyword ability.

    CR 702.64: Flanking is a static ability that triggers when a creature
    with flanking blocks a creature without flanking. The blocked creature
    gets -1/-1 until end of turn.

    Example: "Flanking" — Whenever this blocks a creature without flanking,
    that creature gets -1/-1 until end of turn.
    """

    name = "flanking"

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this permanent has Flanking."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("flanking" in k.lower() for k in keywords)
        has_oracle = bool(_FLANKING_PATTERN.search(oracle))
        return has_keyword or has_oracle

    def apply_flanking(
        self,
        game_state: "GameState",
        flanker: "Permanent",
        blocked: "Permanent",
    ) -> "GameState":
        """Apply flanking: give -1/-1 to blocked creature without flanking.

        Args:
            game_state: Current game state.
            flanker: The creature with flanking that is blocking.
            blocked: The attacking creature being blocked.

        Returns:
            Modified game state with -1/-1 applied.
        """
        # Only apply if blocked creature doesn't have flanking
        if _has_flanking(blocked):
            logger.debug(
                "Flanking not applied: %s also has flanking",
                blocked.card.name,
            )
            return game_state

        # Apply -1/-1 until end of turn
        blocked.power_bonus -= 1
        blocked.toughness_bonus -= 1
        blocked.power_bonus_expires = "end_of_turn"
        blocked.toughness_bonus_expires = "end_of_turn"

        logger.info(
            "Flanking: %s gets -1/-1 until end of turn (blocked by %s)",
            blocked.card.name,
            flanker.card.name,
        )

        return game_state

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply flanking effect (no-op without blocker context)."""
        if target:
            return self.apply_flanking(game_state, permanent, target)
        return game_state

    def get_trigger_description(self) -> str:
        return "Flanking: Blocked creature without flanking gets -1/-1"

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "FlankingKeyword | None":
        """Create FlankingKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            FlankingKeyword if flanking is found, None otherwise.
        """
        if _FLANKING_PATTERN.search(oracle_text):
            return cls()
        return None


def apply_flanking_on_block(
    game_state: GameState,
    attacker: Permanent,
    blocker: Permanent,
) -> GameState:
    """
    Apply flanking when a blocker is declared.

    This is a convenience function for the combat system to call during
    declare blockers. If the blocker has flanking and the attacker doesn't,
    the attacker gets -1/-1 until end of turn.

    Args:
        game_state: Current game state.
        attacker: The attacking creature.
        blocker: The blocking creature.

    Returns:
        Modified game state.
    """
    if _has_flanking(blocker) and not _has_flanking(attacker):
        kw = FlankingKeyword()
        return kw.apply_flanking(game_state, blocker, attacker)
    return game_state


def _has_flanking(perm: Permanent) -> bool:
    """Check if a permanent has the flanking ability."""
    keywords = perm.card.keywords or []
    return any("flanking" in k.lower() for k in keywords)
