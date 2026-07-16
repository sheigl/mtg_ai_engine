"""Dash keyword (CR 702.138).

Dash {cost} is an alternative cost to cast a creature spell. If paid,
the creature gains haste and is returned to its owner's hand at the
beginning of the next end step.
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

logger = logging.getLogger(__name__)

from mtg_engine.models.game import Card

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_DASH_PATTERN = re.compile(
    r"dash\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE
)
_DASH_PLAIN = re.compile(r"\bdash\b", re.IGNORECASE)


class Dash(CostKeyword):
    name = "dash"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("dash" in k.lower() for k in keywords)
            or bool(_DASH_PLAIN.search(oracle))
        )

    @staticmethod
    def has_dash(keywords: list[str]) -> bool:
        return any("dash" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_DASH_PLAIN.search(oracle_text))

    @staticmethod
    def parse_dash_cost(oracle_text: str) -> str | None:
        match = _DASH_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Dash | None:
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_dash_cost(oracle_text))
        return None

    def apply(
        self,
        game_state: GameState,
        perm_on_field: Permanent,
    ) -> GameState:
        """
        Apply Dash keyword effect (CR 702.138).

        When a creature is cast with its dash cost, it gains haste and will be returned
        to its owner's hand at the beginning of the next end step.

        For human players: queue pending_dash_choice on GameState for player to decide.
        For AI players: auto-resolve — pay the cost if affordable, add haste, track in dashed_creatures.

        Args:
            game_state: Current game state.
            perm_on_field: The creature permanent on the battlefield cast with Dash.

        Returns:
            Modified game state with Dash choice queued or resolved.
        """
        from mtg_engine.engine.zones import get_player
        from mtg_engine.engine.mana import can_pay_cost, parse_mana_cost as _parse_cost

        card = perm_on_field.card
        oracle_text = card.oracle_text or ""
        controller = perm_on_field.controller

        # Guard: only process cards that actually have the Dash keyword
        if not self.from_oracle_text(oracle_text):
            logger.debug("%s: %s does not have Dash keyword, returning unchanged state", controller, card.name)
            return game_state.model_copy(update={})

        # Parse Dash cost from oracle text
        dash_cost = self.parse_dash_cost(oracle_text)
        if not dash_cost:
            # No cost specified — pure transform no-op
            logger.debug("%s: Dash on %s has no parseable cost, returning unchanged state", controller, card.name)
            return game_state.model_copy(update={})

        # Determine if player is human or AI
        is_human = (
            getattr(game_state, "human_player_name", None) is not None
            and controller == game_state.human_player_name
        )

        if is_human:
            # Queue Dash choice for human player
            game_state = game_state.model_copy(update={
                "pending_dash_choice": {
                    "player": controller,
                    "card_id": card.id,
                    "permanent_id": perm_on_field.id,
                    "card_name": card.name,
                    "dash_cost": dash_cost,
                    "resolved": False,
                }
            })
            logger.info(
                "%s: queued Dash choice for %s (cost: %s)",
                controller, card.name, dash_cost,
            )
        else:
            # AI auto-resolves Dash: pay cost if affordable, add haste, track dashed creature
            player = get_player(game_state, controller)
            if not player:
                logger.warning("Player not found for Dash resolution: %s", controller)
                return game_state

            can_pay = can_pay_cost(player.mana_pool, dash_cost)

            if can_pay:
                # AI pays Dash cost — deduct mana from pool
                cost_dict = _parse_cost(dash_cost)
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

                new_mana_pool = player.mana_pool.model_copy(update=payment)

                # Add haste to the permanent
                new_keywords = list(perm_on_field.card.keywords or [])
                if "haste" not in [k.lower() for k in new_keywords]:
                    new_keywords.append("haste")

                new_perm = perm_on_field.model_copy(
                    update={"card": perm_on_field.card.model_copy(update={"keywords": new_keywords})}
                )

                # Update battlefield with hasted permanent
                new_battlefield = [
                    p if p.id != perm_on_field.id else new_perm
                    for p in game_state.battlefield
                ]

                # Track dashed creature (perm_id -> owner_player)
                new_dashed = dict(getattr(game_state, "dashed_creatures", {}))
                new_dashed[perm_on_field.id] = controller

                game_state = game_state.model_copy(
                    update={
                        "players": [
                            p.model_copy(update={"mana_pool": new_mana_pool})
                            if p.name == controller else p
                            for p in game_state.players
                        ],
                        "battlefield": new_battlefield,
                        "dashed_creatures": new_dashed,
                        "pending_dash_choice": {
                            "player": controller,
                            "card_id": card.id,
                            "permanent_id": perm_on_field.id,
                            "card_name": card.name,
                            "dash_cost": dash_cost,
                            "resolved": True,
                        }
                    }
                )
                logger.info(
                    "%s: AI resolved Dash for %s (cost: %s, paid: True, haste added)",
                    controller, card.name, dash_cost,
                )
            else:
                # AI can't afford Dash cost — skip
                game_state = game_state.model_copy(update={
                    "pending_dash_choice": {
                        "player": controller,
                        "card_id": card.id,
                        "permanent_id": perm_on_field.id,
                        "card_name": card.name,
                        "dash_cost": dash_cost,
                        "resolved": True,
                    }
                })
                logger.info(
                    "%s: AI skipped Dash for %s (cost: %s, not affordable)",
                    controller, card.name, dash_cost,
                )

        return game_state


def apply_dash(
    game_state: GameState,
    perm_on_field: Permanent,
) -> GameState:
    """
    Module-level convenience function for Dash resolution.

    Args:
        game_state: Current game state.
        perm_on_field: The creature permanent on the battlefield cast with Dash.

    Returns:
        Modified game state with Dash effect applied.
    """
    dash = Dash()
    return dash.apply(game_state, perm_on_field)


def handle_dash_return_to_hand(game_state: GameState) -> GameState:
    """
    Handle returning dashed creatures to their owner's hand at end step (CR 702.138b).

    Called during the beginning of the end step. Returns all tracked dashed creatures
    to their owner's hand and removes them from the battlefield.

    Args:
        game_state: Current game state.

    Returns:
        Modified game state with dashed creatures returned to hand.
    """
    from mtg_engine.engine.zones import get_player

    dashed = getattr(game_state, "dashed_creatures", {}) or {}
    if not dashed:
        return game_state.model_copy(update={})

    # Find all dashed permanents still on battlefield
    perms_to_return = []
    for perm_id, owner in dashed.items():
        perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
        if perm:
            perms_to_return.append((perm, owner))

    if not perms_to_return:
        return game_state.model_copy(update={})

    # Remove all dashed permanents from battlefield and add cards to owners' hands
    new_battlefield = [p for p in game_state.battlefield if p.id not in dashed]

    # Group by owner
    hand_updates: dict[str, list[Card]] = {}
    for perm, owner in perms_to_return:
        player = get_player(game_state, owner)
        current_hand = hand_updates.get(owner, list(player.hand))
        current_hand.append(perm.card)
        hand_updates[owner] = current_hand

    # Build updated players list
    new_players = []
    for p in game_state.players:
        if p.name in hand_updates:
            new_players.append(p.model_copy(update={"hand": hand_updates[p.name]}))
        else:
            new_players.append(p)

    logger.info(
        "Returning %d dashed creature(s) to owner's hand at end step",
        len(perms_to_return),
    )

    return game_state.model_copy(
        update={
            "battlefield": new_battlefield,
            "players": new_players,
            "dashed_creatures": {},  # Clear dashed creatures tracking
        }
    )
