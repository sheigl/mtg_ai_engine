"""Flashback keyword (CR 702.34).

Flashback gives an alternate way to cast a spell from the graveyard.
Pay the flashback cost, then exile the card instead of putting it
anywhere else.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_FLASHBACK_PATTERN = re.compile(
    r"flashback\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE
)
_FLASHBACK_PLAIN = re.compile(r"\bflashback\b", re.IGNORECASE)


class Flashback(CostKeyword):
    name = "flashback"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("flashback" in k.lower() for k in keywords)
            or bool(_FLASHBACK_PLAIN.search(oracle))
        )

    @staticmethod
    def has_flashback(keywords: list[str]) -> bool:
        return any("flashback" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_FLASHBACK_PLAIN.search(oracle_text))

    @staticmethod
    def parse_flashback_cost(oracle_text: str) -> str | None:
        match = _FLASHBACK_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Flashback | None:
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_flashback_cost(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        """
        Apply Flashback keyword effect (CR 702.34).

        Flashback gives an alternate way to cast a spell from the graveyard.
        Pay the flashback cost, then exile the card instead of putting it
        anywhere else.

        This method is called during spell casting to process the Flashback cost payment.
        For human players: queue pending_flashback_exile on GameState for player to decide.
        For AI players: auto-resolve — pay the cost and exile the card.

        Args:
            game_state: Current game state.
            permanent: Permanent with Flashback keyword (the spell being cast).
            target: Optional target permanent (unused for Flashback).

        Returns:
            Modified game state with Flashback choice queued or resolved.
        """
        from mtg_engine.engine.zones import get_player
        from mtg_engine.engine.mana import can_pay_cost, parse_mana_cost as _parse_cost

        card = permanent.card
        oracle_text = card.oracle_text or ""

        # Parse Flashback cost from oracle text
        flashback_cost = self.parse_flashback_cost(oracle_text)
        if not flashback_cost:
            # Return a copy of game state (pure transform pattern)
            return game_state.model_copy(update={})

        # Determine the player (controller of the permanent)
        controller = permanent.controller

        # Determine if player is human or AI
        is_human = (
            getattr(game_state, 'human_player_name', None) is not None
            and controller == game_state.human_player_name
        )

        if is_human:
            # Queue Flashback exile choice for human player
            game_state = game_state.model_copy(update={
                "pending_flashback_exile": {
                    "player": controller,
                    "card_id": card.id,
                    "card_name": card.name,
                    "flashback_cost": flashback_cost,
                    "resolved": False,
                }
            })
            logger.info(
                "%s: queued Flashback exile choice for %s (cost: %s)",
                controller, card.name, flashback_cost
            )
        else:
            # AI auto-resolves Flashback: pay cost and exile the card
            player = get_player(game_state, controller)
            if not player:
                logger.warning("Player not found for Flashback resolution: %s", controller)
                return game_state

            # Check if AI can afford the Flashback cost
            can_pay = can_pay_cost(player.mana_pool, flashback_cost)

            if can_pay:
                # AI decides to pay Flashback cost and exile the card
                cost_dict = _parse_cost(flashback_cost)
                # Calculate how much to pay from each mana pool slot
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
                    # Pay the Flashback cost - update player's mana pool in game state
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
                    "pending_flashback_exile": {
                        "player": controller,
                        "card_id": card.id,
                        "card_name": card.name,
                        "flashback_cost": flashback_cost,
                        "resolved": True,
                    }
                })
                logger.info(
                    "%s: AI resolved Flashback for %s (cost: %s, paid: True, exiled)",
                    controller, card.name, flashback_cost
                )
            else:
                # AI can't afford Flashback cost, skip it
                game_state = game_state.model_copy(update={
                    "pending_flashback_exile": {
                        "player": controller,
                        "card_id": card.id,
                        "card_name": card.name,
                        "flashback_cost": flashback_cost,
                        "resolved": True,
                    }
                })
                logger.info(
                    "%s: AI skipped Flashback for %s (cost: %s, not affordable)",
                    controller, card.name, flashback_cost
                )

        return game_state
