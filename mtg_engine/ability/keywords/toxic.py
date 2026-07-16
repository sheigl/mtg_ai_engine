"""
Toxic keyword ability.

KW-06: Implements the Toxic mechanic.
CR 702.134: "Toxic N" means whenever this creature deals combat damage to
a player, that player gets N poison counters.
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)

# Toxic pattern
_TOXIC_PATTERN = re.compile(r"toxic\s+(\d+)", re.IGNORECASE)


class ToxicKeyword(TriggeredKeyword):
    """Toxic keyword ability.

    CR 702.134: Toxic is a static ability that triggers when the creature
    deals combat damage to a player. The player gets N poison counters
    regardless of how much damage was dealt.

    Example: "Toxic 2" — Whenever this deals combat damage to a player,
    that player gets 2 poison counters.
    """

    name = "toxic"

    def __init__(self, value: int = 1):
        """Initialize Toxic keyword.

        Args:
            value: Number of poison counters to give (N in "Toxic N").
        """
        self.value = value

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this permanent has Toxic."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        # Check both keywords list and oracle text
        has_keyword = any("toxic" in k.lower() for k in keywords)
        has_oracle = bool(_TOXIC_PATTERN.search(oracle))
        return has_keyword or has_oracle

    def get_toxic_value(
        self,
        permanent: "Permanent",
    ) -> int:
        """Get the toxic value from the permanent.

        Args:
            permanent: The creature with toxic.

        Returns:
            Toxic N value, defaults to self.value if not found in card.
        """
        oracle = permanent.card.oracle_text or ""
        match = _TOXIC_PATTERN.search(oracle)
        if match:
            return int(match.group(1))
        return self.value

    def apply_toxic(
        self,
        game_state: "GameState",
        source_perm: "Permanent",
        damaged_player_name: str,
    ) -> "GameState":
        """Apply toxic effect: give poison counters to the damaged player.

        Args:
            game_state: Current game state.
            source_perm: The creature with toxic that dealt damage.
            damaged_player_name: Name of the player who was dealt damage.

        Returns:
            Modified game state with poison counters added.
        """
        toxic_value = self.get_toxic_value(source_perm)

        # Find the damaged player
        for player in game_state.players:
            if player.name == damaged_player_name:
                player.poison_counters += toxic_value
                logger.info(
                    "%s gets %d poison counters from Toxic on %s (total: %d)",
                    player.name,
                    toxic_value,
                    source_perm.card.name,
                    player.poison_counters,
                )
                # Check for lethal poison (10+ poison counters = loss)
                # CR 704.5i: A player with 10+ poison counters loses
                if player.poison_counters >= 10:
                    logger.warning(
                        "%s has %d poison counters and loses the game",
                        player.name,
                        player.poison_counters,
                    )
                break

        return game_state

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply toxic (no-op without damage context)."""
        return game_state

    def get_trigger_description(self) -> str:
        return f"Toxic {self.value}: Give {self.value} poison counters on combat damage"

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "ToxicKeyword | None":
        """Create ToxicKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            ToxicKeyword if toxic is found, None otherwise.
        """
        match = _TOXIC_PATTERN.search(oracle_text)
        if match:
            return cls(value=int(match.group(1)))
        return None
