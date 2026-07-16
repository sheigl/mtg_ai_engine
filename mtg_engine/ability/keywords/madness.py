"""Madness keyword (CR 702.35).

Madness {cost} is a replacement effect that applies when a player would
discard a card with madness. Instead of being put into the graveyard,
it's exiled and may be cast for its madness cost.
"""
from __future__ import annotations
import re
import logging
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_MADNESS_PATTERN = re.compile(
    r"madness\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE
)
_MADNESS_PLAIN = re.compile(r"\bmadness\b", re.IGNORECASE)


class Madness(CostKeyword):
    name = "madness"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("madness" in k.lower() for k in keywords)
            or bool(_MADNESS_PLAIN.search(oracle))
        )

    @staticmethod
    def has_madness(keywords: list[str]) -> bool:
        return any("madness" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_MADNESS_PLAIN.search(oracle_text))

    @staticmethod
    def parse_madness_cost(oracle_text: str) -> str | None:
        match = _MADNESS_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Madness | None:
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_madness_cost(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        """
        Apply Madness keyword effect (CR 702.35).

        When you would discard a card with madness, you may reveal it and pay its
        madness cost. If you do, exile it instead of discarding it. You may cast
        the card this turn.

        This method is called during discard resolution to process the Madness choice.
        For human players: queue pending_madness_choice on GameState for player to decide.
        For AI players: auto-resolve — pay the cost and exile the card if affordable.

        Args:
            game_state: Current game state.
            permanent: Permanent with Madness keyword (the card being discarded).
            target: Optional target permanent (unused for Madness).

        Returns:
            Modified game state with Madness choice queued or resolved.
        """
        from mtg_engine.engine.zones import get_player
        from mtg_engine.engine.mana import can_pay_cost, parse_mana_cost as _parse_cost

        card = permanent.card
        oracle_text = card.oracle_text or ""

        # Parse Madness cost from oracle text
        madness_cost = self.parse_madness_cost(oracle_text)
        if not madness_cost:
            # No cost specified — pure transform no-op
            logger.debug(
                "%s: Madness on %s has no parseable cost, returning unchanged state",
                permanent.controller, card.name,
            )
            return game_state.model_copy(update={})

        # Determine the player (controller of the permanent)
        controller = permanent.controller

        # Determine if player is human or AI
        is_human = (
            getattr(game_state, "human_player_name", None) is not None
            and controller == game_state.human_player_name
        )

        if is_human:
            # Queue Madness choice for human player
            game_state = game_state.model_copy(update={
                "pending_madness_choice": {
                    "player": controller,
                    "card_id": card.id,
                    "card_name": card.name,
                    "madness_cost": madness_cost,
                    "resolved": False,
                }
            })
            logger.info(
                "%s: queued Madness choice for %s (cost: %s)",
                controller, card.name, madness_cost,
            )
        else:
            # AI auto-resolves Madness: pay cost and exile the card if affordable
            player = get_player(game_state, controller)
            if not player:
                logger.warning("Player not found for Madness resolution: %s", controller)
                return game_state

            can_pay = can_pay_cost(player.mana_pool, madness_cost)

            if can_pay:
                # AI decides to pay Madness cost and exile the card
                cost_dict = _parse_cost(madness_cost)
                pool_dict = {
                    "W": player.mana_pool.W, "U": player.mana_pool.U,
                    "B": player.mana_pool.B, "R": player.mana_pool.R,
                    "G": player.mana_pool.G, "C": player.mana_pool.C,
                }
                # Pay colored first
                for color in ("W", "U", "B", "R", "G"):
                    needed = cost_dict.get(color, 0)
                    if needed and pool_dict.get(color, 0) >= needed:
                        pool_dict[color] -= needed
                # Pay generic with whatever's left
                generic_needed = cost_dict.get("generic", 0)
                if generic_needed:
                    pool_available = sum(v for v in pool_dict.values() if v > 0)
                    if pool_available >= generic_needed:
                        pool_dict["C"] -= min(generic_needed, pool_available)

                # Build the update dict for model_copy
                payment = {}
                for color in ("W", "U", "B", "R", "G", "C"):
                    if pool_dict[color] != getattr(player.mana_pool, color, 0):
                        payment[color] = pool_dict[color]

                if payment:
                    new_mana_pool = player.mana_pool.model_copy(update=payment)
                    game_state = game_state.model_copy(
                        update={
                            "players": [
                                p.model_copy(update={"mana_pool": new_mana_pool})
                                if p.name == controller else p
                                for p in game_state.players
                            ]
                        }
                    )

                game_state = game_state.model_copy(update={
                    "pending_madness_choice": {
                        "player": controller,
                        "card_id": card.id,
                        "card_name": card.name,
                        "madness_cost": madness_cost,
                        "resolved": True,
                    }
                })
                logger.info(
                    "%s: AI resolved Madness for %s (cost: %s, paid: True, exiled)",
                    controller, card.name, madness_cost,
                )
            else:
                # AI can't afford Madness cost — skip, card is discarded normally
                game_state = game_state.model_copy(update={
                    "pending_madness_choice": {
                        "player": controller,
                        "card_id": card.id,
                        "card_name": card.name,
                        "madness_cost": madness_cost,
                        "resolved": True,
                    }
                })
                logger.info(
                    "%s: AI skipped Madness for %s (cost: %s, not affordable)",
                    controller, card.name, madness_cost,
                )

        return game_state
