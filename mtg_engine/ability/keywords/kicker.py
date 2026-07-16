"""Kicker keyword (CR 702.33).

Kicker is an additional cost that may be paid as the spell is cast.
Alternative kicker costs may specify different mana or non-mana payments.
"""
from __future__ import annotations
import re
import logging
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_KICKER_PATTERN = re.compile(r"kicker\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE)
_KICKER_PLAIN = re.compile(r"\bkicker\b", re.IGNORECASE)


class Kicker(CostKeyword):
    name = "kicker"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("kicker" in k.lower() for k in keywords)
            or bool(_KICKER_PLAIN.search(oracle))
        )

    @staticmethod
    def has_kicker(keywords: list[str]) -> bool:
        return any("kicker" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_KICKER_PLAIN.search(oracle_text))

    @staticmethod
    def parse_kicker_cost(oracle_text: str) -> str | None:
        match = _KICKER_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Kicker | None:
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_kicker_cost(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        """
        Apply kicker keyword effect (CR 702.33).
        
        Kicker is an additional optional cost that may be paid as the spell is cast.
        If paid, the spell has enhanced effects (kicked=True).
        
        This method is called during spell casting to process the kicker cost payment.
        For human players: queue pending_kicker_choice on GameState for player to decide.
        For AI players: auto-resolve based on available mana.
        
        Args:
            game_state: Current game state.
            permanent: Permanent with kicker keyword (the spell being cast).
            target: Optional target permanent (unused for kicker).
            
        Returns:
            Modified game state with kicker choice queued or resolved.
        """
        from mtg_engine.engine.zones import get_player
        from mtg_engine.engine.mana import can_pay_cost, parse_mana_cost as _parse_cost
        
        card = permanent.card
        oracle_text = card.oracle_text or ""
        
        # Parse kicker cost from oracle text
        kicker_cost = self.parse_kicker_cost(oracle_text)
        if not kicker_cost:
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
            # Queue kicker choice for human player
            game_state = game_state.model_copy(update={
                "pending_kicker_choice": {
                    "player": controller,
                    "card_id": card.id,
                    "card_name": card.name,
                    "kicker_cost": kicker_cost,
                    "base_cost": card.mana_cost or "",
                    "resolved": False,
                }
            })
            logger.info(
                "%s: queued kicker choice for %s (cost: %s, base: %s)",
                controller, card.name, kicker_cost, card.mana_cost or ""
            )
        else:
            # AI auto-resolves kicker based on available mana
            player = get_player(game_state, controller)
            if not player:
                logger.warning("Player not found for kicker resolution: %s", controller)
                return game_state
            
            # Check if AI can afford the kicker cost
            can_pay = can_pay_cost(player.mana_pool, kicker_cost)
            
            if can_pay:
                # AI decides to pay kicker cost
                cost_dict = _parse_cost(kicker_cost)
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
                    # Pay the kicker cost - update player's mana pool in game state
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
                    "pending_kicker_choice": {
                        "player": controller,
                        "card_id": card.id,
                        "card_name": card.name,
                        "kicker_cost": kicker_cost,
                        "base_cost": card.mana_cost or "",
                        "resolved": True,
                    }
                })
                logger.info(
                    "%s: AI resolved kicker for %s (cost: %s, paid: True)",
                    controller, card.name, kicker_cost
                )
            else:
                # AI can't afford kicker cost, skip it
                game_state = game_state.model_copy(update={
                    "pending_kicker_choice": {
                        "player": controller,
                        "card_id": card.id,
                        "card_name": card.name,
                        "kicker_cost": kicker_cost,
                        "base_cost": card.mana_cost or "",
                        "resolved": True,
                    }
                })
                logger.info(
                    "%s: AI skipped kicker for %s (cost: %s, not affordable)",
                    controller, card.name, kicker_cost
                )
        
        return game_state
