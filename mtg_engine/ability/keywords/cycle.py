"""
Type Cycling keyword ability.

KW-08: Implements Type Cycling mechanic.
Type cycling is like cycling but with a mana cost reduction based on
the card's types. "{X}: Discard this card and draw X cards" where X
equals the number of card types.
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Card, Permanent

logger = logging.getLogger(__name__)

# Type cycling pattern
_TYPECYCLING_PATTERN = re.compile(r"type\s+cycling\s*(\{[^}]+\})", re.IGNORECASE)


class TypeCyclingKeyword(TriggeredKeyword):
    """Type Cycling keyword ability.

    Type cycling is an activated ability that lets you discard the card
    and draw cards. The number of cards drawn equals the number of
    different card types the card has.

    Example: "Type cycling {2}" — {2}, Discard this card: Draw a card
    for each type of card this is.
    """

    name = "typecycling"

    def __init__(self, base_cost: str = "", base_draw: int = 1):
        """Initialize Type Cycling keyword.

        Args:
            base_cost: The base mana cost for type cycling.
            base_draw: Base number of cards to draw (modified by types).
        """
        self.base_cost = base_cost
        self.base_draw = base_draw

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Type Cycling."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("typecycling" in k.lower() or "type cycling" in k.lower() for k in keywords)
        has_oracle = bool(_TYPECYCLING_PATTERN.search(oracle))
        return has_keyword or has_oracle

    def get_card_type_count(self, card: "Card") -> int:
        """Count the number of distinct card types.

        Args:
            card: The card to count types for.

        Returns:
            Number of distinct card types (e.g., "Creature — Elf Warrior" = 3).
        """
        type_line = card.type_line or ""
        if not type_line:
            return 1

        # Split on "—" for supertype/type/subtype separation
        parts = type_line.split("—")
        type_count = 0

        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Split on spaces for individual types/subtypes
            tokens = part.split()
            type_count += len(tokens)

        return max(1, type_count)

    def get_draw_count(self, card: "Card") -> int:
        """Get the number of cards to draw based on card types.

        Args:
            card: The card being cycled.

        Returns:
            Number of cards to draw.
        """
        return self.get_card_type_count(card)

    def type_cycle(
        self,
        game_state: "GameState",
        card: "Card",
        controller_name: str,
    ) -> "GameState":
        """Execute type cycling: discard and draw cards.

        Args:
            game_state: Current game state.
            card: The card to cycle.
            controller_name: Name of the player cycling the card.

        Returns:
            Modified game state with cards drawn.
        """
        draw_count = self.get_draw_count(card)
        controller = None
        for player in game_state.players:
            if player.name == controller_name:
                controller = player
                break

        if not controller:
            return game_state

        # Remove from hand and add to graveyard
        if card in controller.hand:
            controller.hand.remove(card)
            controller.graveyard.append(card)

        # Draw cards
        for _ in range(draw_count):
            if controller.library:
                drawn = controller.library.pop(0)
                controller.hand.append(drawn)

        logger.info(
            "%s type-cycled %s (types: %d) and drew %d cards",
            controller_name,
            card.name,
            self.get_card_type_count(card),
            draw_count,
        )

        return game_state

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply type cycling (no-op without hand context)."""
        return game_state

    def get_trigger_description(self) -> str:
        return f"Type cycling {self.base_cost}: Draw cards = number of types"

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "TypeCyclingKeyword | None":
        """Create TypeCyclingKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            TypeCyclingKeyword if type cycling is found, None otherwise.
        """
        match = _TYPECYCLING_PATTERN.search(oracle_text)
        if match:
            return cls(base_cost=match.group(1))
        return None
