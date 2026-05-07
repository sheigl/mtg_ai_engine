"""
Meld keyword ability.

KW-07: Implements the Meld mechanic.
CR 702.125: Meld is a static ability of two cards. When either card is
put into a graveyard, its owner may reveal the other card from their
library and put both face down. At the start of the next turn, the
merged card is put onto the battlefield face up.
"""
from __future__ import annotations
import logging
import re
import uuid
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import TriggeredKeyword
from mtg_engine.models.game import Card

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)

# Meld pattern: "Meld — <merged card name>"
_MELD_PATTERN = re.compile(r"meld\s*[–—-]\s*(.+)", re.IGNORECASE)


class MeldKeyword(TriggeredKeyword):
    """Meld keyword ability.

    CR 702.125: Meld creates a merged card from two MDFC (modal double-faced card)
    halves. When one half is put into a graveyard from the battlefield, the player
    may reveal the other half from their library. Both are put face down, then
    the merged card enters the battlefield at the start of the next turn.

    Example:
        Card A: "Meld — <Merged Card Name>"
        Card B: "Meld — <Merged Card Name>"
    """

    name = "meld"

    def __init__(
        self,
        merged_card_name: str = "",
        partner_card_name: str = "",
    ):
        """Initialize Meld keyword.

        Args:
            merged_card_name: Name of the merged card on the other face.
            partner_card_name: Name of the partner card that melds with this one.
        """
        self.merged_card_name = merged_card_name
        self.partner_card_name = partner_card_name

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this permanent has Meld."""
        oracle = permanent.card.oracle_text or ""
        return bool(_MELD_PATTERN.search(oracle))

    def get_merged_card_name(self, permanent: "Permanent") -> str:
        """Get the name of the merged card.

        Args:
            permanent: The permanent with meld.

        Returns:
            Name of the merged card.
        """
        if self.merged_card_name:
            return self.merged_card_name
        oracle = permanent.card.oracle_text or ""
        match = _MELD_PATTERN.search(oracle)
        if match:
            return match.group(1).strip()
        return ""

    def start_meld(
        self,
        game_state: "GameState",
        source_perm: "Permanent",
        controller_name: str,
    ) -> "GameState":
        """Initiate the meld process.

        This is called when a meld card is put into a graveyard from the battlefield.
        The player reveals the partner card from their library and puts both face down.

        Args:
            game_state: Current game state.
            source_perm: The permanent that went to the graveyard.
            controller_name: Name of the player controlling the meld.

        Returns:
            Modified game state with meld in progress.
        """
        controller = None
        for player in game_state.players:
            if player.name == controller_name:
                controller = player
                break

        if not controller:
            return game_state

        merged_name = self.get_merged_card_name(source_perm)
        partner_name = self.partner_card_name

        logger.info(
            "Meld initiated: %s + %s → %s (controller: %s)",
            source_perm.card.name,
            partner_name,
            merged_name,
            controller_name,
        )

        # Mark the meld state in the game
        if not hasattr(game_state, "_meld_in_progress"):
            game_state._meld_in_progress = {}

        game_state._meld_in_progress[controller_name] = {
            "merged_card_name": merged_name,
            "partner_card_name": partner_name,
            "first_card": source_perm.card.name,
        }

        return game_state

    def complete_meld(
        self,
        game_state: "GameState",
        controller_name: str,
    ) -> "GameState":
        """Complete the meld: put the merged card onto the battlefield.

        Called at the start of the controller's turn after meld was initiated.

        Args:
            game_state: Current game state.
            controller_name: Name of the player completing the meld.

        Returns:
            Modified game state with the merged card on the battlefield.
        """
        meld_state = getattr(game_state, "_meld_in_progress", None)
        if not meld_state or controller_name not in meld_state:
            return game_state

        meld_info = meld_state.pop(controller_name)
        merged_name = meld_info["merged_card_name"]

        # Create the merged card
        merged_card = Card(
            id=str(uuid.uuid4()),
            name=merged_name,
            type_line="Legendary Creature",
            oracle_text=f"Meld of {meld_info['first_card']} and {meld_info['partner_card_name']}",
        )

        # Put onto battlefield
        from mtg_engine.engine.zones import put_permanent_onto_battlefield
        game_state, _ = put_permanent_onto_battlefield(
            game_state, merged_card, controller_name
        )

        logger.info(
            "Meld complete: %s entered the battlefield under %s's control",
            merged_name,
            controller_name,
        )

        return game_state

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply meld (no-op without graveyard context)."""
        return game_state

    def get_trigger_description(self) -> str:
        return f"Meld → {self.merged_card_name}"

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "MeldKeyword | None":
        """Create MeldKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            MeldKeyword if meld is found, None otherwise.
        """
        match = _MELD_PATTERN.search(oracle_text)
        if match:
            return cls(merged_card_name=match.group(1).strip())
        return None
