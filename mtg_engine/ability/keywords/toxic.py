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

        CR 702.134a: Whenever a toxic creature deals combat damage to a
        player, that player gets N poison counters — once per combat damage
        event, regardless of the amount of damage dealt.

        Pure transform: returns a new GameState via model_copy(update={...}).
        Never mutates the live player. No-op (returns the same object) when
        the toxic value is 0 or the target player is not in the game.

        The 10+ poison counters loss condition (CR 704.5c) is NOT handled
        here — the SBA (engine/sba.py) checks poison counters and marks the
        player as having lost.

        Args:
            game_state: Current game state.
            source_perm: The creature with toxic that dealt damage.
            damaged_player_name: Name of the player who was dealt damage.

        Returns:
            New game state with poison counters added to the damaged player.
        """
        toxic_value = self.get_toxic_value(source_perm)
        if toxic_value <= 0:
            return game_state

        found = False
        new_players: list = []
        for player in game_state.players:
            if player.name == damaged_player_name:
                new_count = player.poison_counters + toxic_value
                new_players.append(player.model_copy(update={"poison_counters": new_count}))
                found = True
                logger.info(
                    "%s gets %d poison counters from Toxic on %s (total: %d); "
                    "SBA will check for loss at 10+ (CR 704.5c)",
                    player.name,
                    toxic_value,
                    source_perm.card.name,
                    new_count,
                )
            else:
                new_players.append(player)

        if not found:
            return game_state

        return game_state.model_copy(update={"players": new_players})

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


def apply_toxic(
    game_state: "GameState",
    source_perm: "Permanent",
    damaged_player_name: str,
) -> "GameState":
    """Module-level convenience: apply toxic to the damaged player (CR 702.134a).

    Called from the combat damage flow (engine/combat/core.py) when a toxic
    source deals combat damage to a player. The toxic value is parsed from
    the source card's oracle text ("Toxic N"); defaults to 1 when the oracle
    text has no explicit value.

    Pure transform: returns a new GameState via model_copy(update={...}), or
    the same object when nothing changes. Loss at 10+ poison counters is
    handled by the SBA (CR 704.5c), not here.

    Args:
        game_state: Current game state.
        source_perm: The toxic creature that dealt combat damage.
        damaged_player_name: Name of the player dealt combat damage.

    Returns:
        New game state with poison counters added to the damaged player.
    """
    oracle = source_perm.card.oracle_text or ""
    keyword = ToxicKeyword.from_oracle(oracle) or ToxicKeyword()
    return keyword.apply_toxic(game_state, source_perm, damaged_player_name)
