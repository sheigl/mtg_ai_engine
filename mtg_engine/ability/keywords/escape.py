"""Escape keyword (CR 702.45).

Escape {cost} — {cost}, Exile N other cards from your graveyard:
Cast this card from your graveyard. If you cast it this way, it
exiles on leaving the battlefield.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_ESCAPE_COST_PATTERN = re.compile(
    r"escape\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE
)
_ESCAPE_EXILE_PATTERN = re.compile(r"(?:exile|escape)\s+(\w+)\s+other", re.IGNORECASE)
_ESCAPE_PLAIN = re.compile(r"\bescape\b", re.IGNORECASE)


class Escape(CostKeyword):
    name = "escape"

    def __init__(self, cost: str | None = None, exile_count: int = 0):
        self.cost = cost
        self.exile_count = exile_count

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("escape" in k.lower() for k in keywords)
            or bool(_ESCAPE_PLAIN.search(oracle))
        )

    @staticmethod
    def has_escape(keywords: list[str]) -> bool:
        return any("escape" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_ESCAPE_PLAIN.search(oracle_text))

    @staticmethod
    def parse_escape_cost(oracle_text: str) -> str | None:
        match = _ESCAPE_COST_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def parse_exile_count(oracle_text: str) -> int:
        match = _ESCAPE_EXILE_PATTERN.search(oracle_text or "")
        if match:
            word = match.group(1)
            # Numeric string like "3"
            if word.isdigit():
                return int(word)
            # Word number like "three"
            number_map = {
                "one": 1, "two": 2, "three": 3, "four": 4,
                "five": 5, "six": 6, "seven": 7, "eight": 8,
                "nine": 9, "ten": 10,
            }
            return number_map.get(word.lower(), 1)
        return 0

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Escape | None:
        if cls.from_oracle_text(oracle_text):
            return cls(
                cost=cls.parse_escape_cost(oracle_text),
                exile_count=cls.parse_exile_count(oracle_text),
            )
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        """
        Apply Escape keyword effect (CR 702.45).

        Escape lets you cast a legendary card from exile by paying its
        escape cost. Similar to Flashback but for exile zone instead of
        graveyard.

        This method is called during spell casting to process the Escape cost payment.
        For human players: queue pending_escape_exile on GameState for player to decide.
        For AI players: auto-resolve — pay the cost and exile the card.

        Args:
            game_state: Current game state.
            permanent: Permanent with Escape keyword (the spell being cast).
            target: Optional target permanent (unused for Escape).

        Returns:
            Modified game state with Escape choice queued or resolved.
        """
        from mtg_engine.engine.zones import get_player
        from mtg_engine.engine.mana import can_pay_cost, parse_mana_cost as _parse_cost

        card = permanent.card
        oracle_text = card.oracle_text or ""

        # Parse Escape cost from oracle text
        escape_cost = self.parse_escape_cost(oracle_text)
        if not escape_cost:
            # Return a copy of game state (pure transform pattern)
            return game_state.model_copy(update={})

        # Determine the player (controller of the permanent in exile)
        controller = permanent.controller

        # Determine if player is human or AI
        is_human = (
            getattr(game_state, 'human_player_name', None) is not None
            and controller == game_state.human_player_name
        )

        # Parse exile count from oracle text (e.g., "Escape 3 other cards from your graveyard")
        exile_count = self.parse_exile_count(oracle_text)

        if is_human:
            # Queue Escape exile choice for human player
            game_state = game_state.model_copy(update={
                "pending_escape_exile": {
                    "player": controller,
                    "card_id": card.id,
                    "card_name": card.name,
                    "escape_cost": escape_cost,
                    "exile_count": exile_count,
                    "resolved": False,
                }
            })
            logger.info(
                "%s: queued Escape exile choice for %s (cost: %s, exile %d cards)",
                controller, card.name, escape_cost, exile_count
            )
        else:
            # AI auto-resolves Escape: pay cost and exile the card
            player = get_player(game_state, controller)
            if not player:
                logger.warning("Player not found for Escape resolution: %s", controller)
                return game_state

            # Check if AI can afford the Escape cost
            can_pay = can_pay_cost(player.mana_pool, escape_cost)

            if can_pay:
                # AI decides to pay Escape cost and exile the card
                cost_dict = _parse_cost(escape_cost)
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
                    # Pay the Escape cost - update player's mana pool in game state
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
                    "pending_escape_exile": {
                        "player": controller,
                        "card_id": card.id,
                        "card_name": card.name,
                        "escape_cost": escape_cost,
                        "exile_count": exile_count,
                        "resolved": True,
                    }
                })
                logger.info(
                    "%s: AI resolved Escape for %s (cost: %s, paid: True, exiled)",
                    controller, card.name, escape_cost
                )
            else:
                # AI can't afford Escape cost, skip it
                game_state = game_state.model_copy(update={
                    "pending_escape_exile": {
                        "player": controller,
                        "card_id": card.id,
                        "card_name": card.name,
                        "escape_cost": escape_cost,
                        "exile_count": exile_count,
                        "resolved": True,
                    }
                })
                logger.info(
                    "%s: AI skipped Escape for %s (cost: %s, not affordable)",
                    controller, card.name, escape_cost
                )

        return game_state
