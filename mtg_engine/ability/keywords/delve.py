"""Delve keyword (CR 702.86).

Delve allows exiling cards from your graveyard to help pay for a spell's
mana cost. Each card exiled reduces the non-{W}/{B}/{U}/{R}/{G} cost to
pay by {1}.
"""
from __future__ import annotations
import re
import logging
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_DELVE_PATTERN = re.compile(r"\bdelve\s*(\{[^}]+\})?", re.IGNORECASE)
_DELVE_COUNT_PATTERN = re.compile(r"\bexile\s+(\d+|\w+)", re.IGNORECASE)


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

    @staticmethod
    def parse_delve_cost(oracle_text: str) -> str | None:
        """
        Parse Delve cost from oracle text.
        CR 702.86: Delve {cost} — {cost}, Exile N cards from your graveyard
        while casting this spell, paying {1} for each card exiled.
        Returns the mana cost portion (e.g., "{2}{U}"), or None if no cost specified.
        """
        # Match "Delve" followed by one or more {X} blocks
        match = re.search(r"\bdelve\s+(\{(?:[^}]+}\s*)+)", oracle_text or "", re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def parse_delve_count(oracle_text: str) -> int:
        """
        Parse the number of cards to exile from Delve text.
        CR 702.86: The number follows "Exile" (e.g., "Exile 1 card" or "Exile 3 cards").
        If no specific count is given, defaults to the generic mana cost.
        """
        match = _DELVE_COUNT_PATTERN.search(oracle_text or "")
        if match:
            word = match.group(1)
            if word.isdigit():
                return int(word)
            number_map = {
                "one": 1, "two": 2, "three": 3, "four": 4,
                "five": 5, "six": 6, "seven": 7, "eight": 8,
                "nine": 9, "ten": 10,
            }
            return number_map.get(word.lower(), 1)
        return 0

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        """
        Apply Delve keyword effect (CR 702.86).

        Delve allows exiling cards from your graveyard to help pay for a
        spell's mana cost. Each card exiled reduces the non-{W}/{B}/{U}/{R}/{G}
        cost to pay for the spell by {1}.

        This method is called during spell casting to process the Delve cost payment.
        For human players: queue pending_delve_choice on GameState for player to decide
        how many cards to exile (0 up to generic cost).
        For AI players: auto-exile cards from graveyard up to available mana needed.

        Args:
            game_state: Current game state.
            permanent: Permanent with Delve keyword (the spell being cast).
            target: Optional target permanent (unused for Delve).

        Returns:
            Modified game state with Delve choice queued or resolved.
        """
        from mtg_engine.engine.zones import get_player
        from mtg_engine.engine.mana import parse_mana_cost as _parse_cost

        card = permanent.card
        oracle_text = card.oracle_text or ""

        # Guard: only process if this card actually has Delve
        if not self.applies(game_state, permanent):
            return game_state.model_copy(update={})

        # Parse optional explicit delve cost from oracle text (e.g., "Delve {2}{U}")
        # Note: standard Delve has no separate cost — it just reduces generic cost by exiling
        # graveyard cards. This field captures any non-standard variant costs.
        delve_cost = self.parse_delve_cost(oracle_text)

        # Determine the player (controller of the permanent)
        controller = permanent.controller

        # Parse the mana cost to determine max generic reduction available via Delve
        mana_cost = card.mana_cost or ""
        cost_dict = _parse_cost(mana_cost)
        generic_cost = cost_dict.get("generic", 0)

        if generic_cost <= 0:
            # No generic cost to reduce — Delve has no effect, pure transform return
            logger.debug(
                "%s: Delve on %s has no generic cost to reduce (mana_cost=%s)",
                controller, card.name, mana_cost,
            )
            return game_state.model_copy(update={})

        # Determine if player is human or AI
        is_human = (
            getattr(game_state, "human_player_name", None) is not None
            and controller == game_state.human_player_name
        )

        if is_human:
            # Queue Delve exile choice for human player
            # Human decides how many cards to exile (0 up to generic_cost)
            game_state = game_state.model_copy(update={
                "pending_delve_choice": {
                    "player": controller,
                    "card_id": card.id,
                    "card_name": card.name,
                    "delve_cost": delve_cost,
                    "cards_to_exile": generic_cost,
                    "card_ids": [],  # Populated by API during resolution
                    "resolved": False,
                }
            })
            logger.info(
                "%s: queued Delve exile choice for %s (delve_cost=%s, up to %d cards)",
                controller, card.name, delve_cost, generic_cost,
            )
        else:
            # AI auto-resolves Delve: select graveyard cards to exile
            player = get_player(game_state, controller)
            if not player:
                logger.warning("Player not found for Delve resolution: %s", controller)
                return game_state

            # Exile up to generic_cost cards from graveyard (oldest first)
            graveyard_size = len(player.graveyard)
            actual_exile = min(generic_cost, graveyard_size)

            card_ids: list[str] = []
            if actual_exile > 0 and player.graveyard:
                selected = player.graveyard[:actual_exile]
                card_ids = [c.id for c in selected]

            game_state = game_state.model_copy(update={
                "pending_delve_choice": {
                    "player": controller,
                    "card_id": card.id,
                    "card_name": card.name,
                    "delve_cost": delve_cost,
                    "cards_to_exile": actual_exile,
                    "card_ids": card_ids,
                    "resolved": True,
                }
            })

            if actual_exile > 0:
                logger.info(
                    "%s: AI resolved Delve for %s (exiling %d cards, IDs: %s)",
                    controller, card.name, actual_exile, card_ids,
                )
            else:
                logger.info(
                    "%s: AI skipped Delve for %s (no graveyard cards available)",
                    controller, card.name,
                )

        return game_state
