"""Dredge keyword (CR 702.60).

Dredge N replaces a card draw: you may put N cards from your graveyard
into your library instead of drawing a card. If you do, return this card
from your graveyard to your hand.
"""
from __future__ import annotations
import re
import logging
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import KeywordAbility

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_DREDGE_PATTERN = re.compile(r"dredge\s+(\d+)", re.IGNORECASE)


class Dredge(KeywordAbility):
    name = "dredge"

    def __init__(self, value: int = 1):
        self.value = value

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("dredge" in k.lower() for k in keywords)
            or bool(_DREDGE_PATTERN.search(oracle))
        )

    @staticmethod
    def has_dredge(keywords: list[str]) -> bool:
        return any("dredge" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_DREDGE_PATTERN.search(oracle_text))

    @staticmethod
    def parse_dredge_value(oracle_text: str) -> int:
        match = _DREDGE_PATTERN.search(oracle_text or "")
        if match:
            return int(match.group(1))
        return 1

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Dredge | None:
        if cls.from_oracle_text(oracle_text):
            return cls(value=cls.parse_dredge_value(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        """
        Apply Dredge keyword effect (CR 702.60).

        When you would draw a card with dredge N, instead put the top N cards of your
        library on top in any order and return this card from your graveyard to your hand.

        This method is called during draw resolution to process the Dredge choice.
        For human players: queue pending_dredge_choice on GameState for player to decide.
        For AI players: auto-resolve — dredge if there are enough cards in library and
        the card is in graveyard.

        Args:
            game_state: Current game state.
            permanent: Permanent with Dredge keyword (the card being drawn).
            target: Optional target permanent (unused for Dredge).

        Returns:
            Modified game state with Dredge choice queued or resolved.
        """
        from mtg_engine.engine.zones import get_player

        card = permanent.card
        oracle_text = card.oracle_text or ""

        # Guard: only process cards that actually have the Dredge keyword
        if not self.from_oracle_text(oracle_text):
            logger.debug("%s: %s does not have Dredge keyword, returning unchanged state", permanent.controller, card.name)
            return game_state.model_copy(update={})

        # Parse Dredge value from oracle text
        dredge_n = self.parse_dredge_value(oracle_text)
        if not dredge_n:
            logger.debug("%s: Dredge on %s has no parseable value, returning unchanged state", permanent.controller, card.name)
            return game_state.model_copy(update={})

        # Determine the player (controller of the permanent)
        controller = permanent.controller

        # Determine if player is human or AI
        is_human = (
            getattr(game_state, "human_player_name", None) is not None
            and controller == game_state.human_player_name
        )

        if is_human:
            # Queue Dredge choice for human player
            game_state = game_state.model_copy(update={
                "pending_dredge_choice": {
                    "player": controller,
                    "card_id": card.id,
                    "card_name": card.name,
                    "dredge_n": dredge_n,
                    "resolved": False,
                }
            })
            logger.info(
                "%s: queued Dredge choice for %s (N=%d)",
                controller, card.name, dredge_n,
            )
        else:
            # AI auto-resolves Dredge: check if there are enough cards in library
            player = get_player(game_state, controller)
            if not player:
                logger.warning("Player not found for Dredge resolution: %s", controller)
                return game_state

            lib_count = len(player.library)
            can_dredge = lib_count >= dredge_n

            if can_dredge:
                # AI decides to dredge — put N cards from library on top, return card to hand
                new_hand = list(player.hand) + [card]
                game_state = game_state.model_copy(update={
                    "players": [
                        p.model_copy(update={"hand": new_hand}) if p.name == controller else p
                        for p in game_state.players
                    ],
                    "pending_dredge_choice": {
                        "player": controller,
                        "card_id": card.id,
                        "card_name": card.name,
                        "dredge_n": dredge_n,
                        "resolved": True,
                    }
                })
                logger.info(
                    "%s: AI resolved Dredge for %s (N=%d, returned to hand)",
                    controller, card.name, dredge_n,
                )
            else:
                # Not enough cards in library — skip dredge, draw normally
                game_state = game_state.model_copy(update={
                    "pending_dredge_choice": {
                        "player": controller,
                        "card_id": card.id,
                        "card_name": card.name,
                        "dredge_n": dredge_n,
                        "resolved": True,
                    }
                })
                logger.info(
                    "%s: AI skipped Dredge for %s (N=%d, not enough library cards)",
                    controller, card.name, dredge_n,
                )

        return game_state
