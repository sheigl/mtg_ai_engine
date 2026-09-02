"""Evoke keyword ability (CR 702.45).

Evoke {cost} is an alternative cost that may be paid instead of paying a
creature spell's mana cost. The creature enters the battlefield with this
ability, and as it enters, it's sacrificed.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import TriggeredKeyword
from mtg_engine.models.game import PendingTrigger

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Card, Permanent

_EVOKE_PATTERN = re.compile(r"\bEvoke\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_EVOKE_PLAIN = re.compile(r"\bEvoke\b", re.IGNORECASE)


class EvokeKeyword(TriggeredKeyword):
    """Evoke keyword ability.

    CR 702.45: "Evoke {cost}" means "{cost} rather than pay this creature card's
    mana cost to cast it." An evoked creature enters the battlefield with an
    ability that causes it to be sacrificed as it enters the battlefield.

    Example: "Evoke {1}{B}" — Pay {1}{B} instead of mana cost; sacrifice as it enters.
    """

    name = "evoke"
    trigger_type = "evoke"

    def __init__(self, cost: str | None = None):
        """Initialize Evoke keyword.

        Args:
            cost: The alternative mana cost for evoking (e.g., "{1}{B}").
        """
        self.cost = cost

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Evoke."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("evoke" in k.lower() for k in keywords)
        has_oracle = bool(_EVOKE_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_evoke(keywords: list[str]) -> bool:
        """Check if a keyword list contains evoke."""
        return any("evoke" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains evoke."""
        if not oracle_text:
            return False
        return bool(_EVOKE_PLAIN.search(oracle_text))

    @staticmethod
    def parse_evoke_cost(oracle_text: str) -> str | None:
        """Parse the evoke cost from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Cost string (e.g., "{1}{B}") or None if not found.
        """
        match = _EVOKE_PATTERN.search(oracle_text or "")
        if match:
            return match.group("cost").strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "EvokeKeyword | None":
        """Create EvokeKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            EvokeKeyword if evoke is found, None otherwise.
        """
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_evoke_cost(oracle_text))
        return None

    def create_trigger(self, card: "Card", controller: str, perm_id: str | None = None) -> "PendingTrigger":
        """Create an evoke trigger.

        Args:
            card: The evoked card.
            controller: Player who evoked the card.
            perm_id: Permanent ID of the evoked creature.

        Returns:
            PendingTrigger representing the evoke sacrifice effect.
        """
        return PendingTrigger(
            source_permanent_id=perm_id or "",
            controller=controller,
            trigger_type=self.trigger_type,
            effect_description=f"Evoke {self.cost}: Sacrifice this creature as it enters",
            source_card_name=card.name if card else "Unknown",
        )

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply evoke (no-op without spell casting context)."""
        return game_state

    def queue_sacrifice(
        self,
        game_state: "GameState",
        permanent_id: str,
        player_name: str,
        card_name: str,
    ) -> "GameState":
        """Queue a mandatory evoke sacrifice for the end step.

        Pure transform: returns new GameState via model_copy.

        Args:
            game_state: Current game state.
            permanent_id: ID of the evoked creature on battlefield.
            player_name: Controller of the evoked creature.
            card_name: Name of the card for logging/display.

        Returns:
            New GameState with pending_evoke_sacrifice set.
        """
        logger.info("Evoke: queued mandatory sacrifice for %s (%s)", permanent_id, card_name)

        return game_state.model_copy(
            update={
                "pending_evoke_sacrifice": {
                    "player": player_name,
                    "permanent_id": permanent_id,
                    "card_name": card_name,
                }
            }
        )

    def resolve_sacrifice(self, game_state: "GameState") -> "GameState":
        """Execute the mandatory evoke sacrifice.

        Moves the permanent to graveyard and clears pending state.
        Pure transform: returns new GameState via model_copy.

        Args:
            game_state: Current game state with pending_evoke_sacrifice set.

        Returns:
            New GameState with the creature sacrificed (moved to graveyard).
        """
        if not game_state.pending_evoke_sacrifice:
            return game_state

        perm_id = game_state.pending_evoke_sacrifice["permanent_id"]

        # Find the permanent on battlefield
        perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
        if perm is None:
            logger.warning("Evoke sacrifice: %s not found on battlefield, clearing", perm_id)
            return game_state.model_copy(update={"pending_evoke_sacrifice": None})

        # Use centralized sacrifice helper (wires sacrifice triggers)
        from mtg_engine.engine.zones import _sacrifice_permanent as _do_sacrifice
        game_state = _do_sacrifice(game_state, perm_id)

        logger.info("Evoke: sacrificed %s (%s)", perm_id, game_state.pending_evoke_sacrifice["card_name"])

        return game_state.model_copy(
            update={
                "pending_evoke_sacrifice": None,
            }
        )

    def get_trigger_description(self) -> str:
        cost_str = self.cost or "{1}{B}"
        return f"Evoke {cost_str}: Pay to cast; sacrifice as it enters the battlefield"


# --- Module-level convenience functions ---

def queue_sacrifice(
    game_state: "GameState",
    permanent_id: str,
    player_name: str,
    card_name: str,
) -> "GameState":
    """Queue a mandatory evoke sacrifice for the end step.

    Convenience wrapper around EvokeKeyword.queue_sacrifice().
    """
    return EvokeKeyword().queue_sacrifice(game_state, permanent_id, player_name, card_name)


def resolve_sacrifice(game_state: "GameState") -> "GameState":
    """Execute the mandatory evoke sacrifice.

    Convenience wrapper around EvokeKeyword.resolve_sacrifice().
    """
    return EvokeKeyword().resolve_sacrifice(game_state)


def resolve_with_ai(game_state: "GameState") -> "GameState":
    """AI auto-resolves evoke sacrifice (always sacrifices as mandatory)."""
    return resolve_sacrifice(game_state)
