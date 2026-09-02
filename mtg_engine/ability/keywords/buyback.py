"""Buyback keyword ability (CR 702.28).

Buyback {cost} is an additional cost that may be paid as a sorcery spell
is cast. If you pay the buyback cost, the spell returns to your hand instead
of going to your graveyard when it resolves.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import Card, GameState, Permanent

_BUYBACK_PATTERN = re.compile(r"\bBuyback\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_BUYBACK_PLAIN = re.compile(r"\bBuyback\b", re.IGNORECASE)


def _is_sorcery_speed_spell(card: "Card") -> bool:
    """Return True if the card is a sorcery-speed spell (CR 702.27).

    Buyback only applies to sorceries: the type line must contain
    "Sorcery" (e.g. "Sorcery", "Enchantment — Sorcery", "Legendary
    Enchantment — Sorcery"). Instants, creatures, and non-spell card types
    are NOT sorcery-speed, so buyback is silently ignored for them.
    """
    type_line = (card.type_line or "").lower()
    return "sorcery" in type_line


class BuybackKeyword(CostKeyword):
    """Buyback keyword ability.

    CR 702.28: "Buyback {cost}" is an additional cost that may be paid as a
    sorcery spell is cast. If you pay the buyback cost, return this spell to
    its owner's hand instead of putting it into their graveyard when it resolves.

    Example: "Buyback {3}{B}" — Pay {3}{B} to return this spell to your hand.
    """

    name = "buyback"

    def __init__(self, cost: str | None = None):
        """Initialize Buyback keyword.

        Args:
            cost: The additional mana cost for buyback (e.g., "{3}{B}").
        """
        self.cost = cost

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Buyback."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("buyback" in k.lower() for k in keywords)
        has_oracle = bool(_BUYBACK_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_buyback(keywords: list[str]) -> bool:
        """Check if a keyword list contains buyback."""
        return any("buyback" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains buyback."""
        if not oracle_text:
            return False
        return bool(_BUYBACK_PLAIN.search(oracle_text))

    @staticmethod
    def parse_buyback_cost(oracle_text: str) -> str | None:
        """Parse the buyback cost from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Cost string (e.g., "{3}{B}") or None if not found.
        """
        match = _BUYBACK_PATTERN.search(oracle_text or "")
        if match:
            return match.group("cost").strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "BuybackKeyword | None":
        """Create BuybackKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            BuybackKeyword if buyback is found, None otherwise.
        """
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_buyback_cost(oracle_text))
        return None

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply buyback (CR 702.27/702.28).

        Buyback {cost} is an ADDITIONAL cost that may be paid as a sorcery
        spell is cast. If paid, the spell returns to its owner's hand instead
        of going to their graveyard when it resolves.

        Called during spell declaration (the card controller is the caster and
        ``permanent`` is the spell in hand being cast).

        - Human caster: queues ``pending_buyback_choice`` on the GameState
          (resolved=False, paid=False). The cast is deferred until the
          ``buyback_pay`` / ``buyback_pass`` choice handler re-drives it.
        - AI caster: auto-resolves — ``pending_buyback_choice`` is set with
          resolved=True and ``paid=True`` iff the pool can cover the base cost
          PLUS the buyback cost (heuristic: pay if extra mana is available
          after the base cost is already paid). The actual deduction happens
          in ``cast_spell`` (spell declaration), which appends the buyback
          cost to the base cost when the ``buyback_paid`` flag is set.
        - No-op (returns the SAME game_state object): card has no buyback, no
          parseable buyback cost, or the card is not a sorcery-speed spell
          (buyback only applies to sorceries — creatures, instants, and
          activated abilities are silently ignored).

        Args:
            game_state: Current game state.
            permanent: The spell being cast (controller = the caster).
            target: Optional target (unused for buyback).

        Returns:
            Modified game state with ``pending_buyback_choice`` set, or the
            same object on no-op.
        """
        from mtg_engine.engine.mana import can_pay_cost
        from mtg_engine.engine.zones import get_player

        card = permanent.card
        oracle_text = card.oracle_text or ""

        # No-op guard 1: card must have buyback (keyword list or oracle text).
        if not (
            self.has_buyback(card.keywords or [])
            or bool(_BUYBACK_PLAIN.search(oracle_text))
        ):
            return game_state

        # No-op guard 2: buyback requires a parseable cost ("Buyback {cost}").
        buyback_cost = self.parse_buyback_cost(oracle_text)
        if not buyback_cost:
            return game_state

        # No-op guard 3: buyback is an additional cost on sorcery spells only
        # (CR 702.27). Creatures, instants, and non-sorcery-speed spells are
        # silently ignored.
        if not _is_sorcery_speed_spell(card):
            return game_state

        controller = permanent.controller

        # Human vs AI (same convention as Kicker): the human is identified by
        # GameState.human_player_name; everyone else auto-resolves.
        is_human = (
            getattr(game_state, "human_player_name", None) is not None
            and controller == game_state.human_player_name
        )

        if is_human:
            # Queue the buyback choice — the cast is deferred to the API
            # choice handler (buyback_pay / buyback_pass).
            game_state = game_state.model_copy(update={
                "pending_buyback_choice": {
                    "player": controller,
                    "card_id": card.id,
                    "card_name": card.name,
                    "buyback_cost": buyback_cost,
                    "base_cost": card.mana_cost or "",
                    "resolved": False,
                    "paid": False,
                }
            })
            logger.info(
                "%s: queued buyback choice for %s (cost: %s, base: %s)",
                controller, card.name, buyback_cost, card.mana_cost or ""
            )
            return game_state

        # AI auto-resolution: pay if the pool covers base + buyback.
        player = get_player(game_state, controller)
        if player is None:
            logger.warning(
                "Player not found for buyback resolution: %s", controller
            )
            return game_state

        combined_cost = (card.mana_cost or "") + buyback_cost
        paid = can_pay_cost(player.mana_pool, combined_cost)

        game_state = game_state.model_copy(update={
            "pending_buyback_choice": {
                "player": controller,
                "card_id": card.id,
                "card_name": card.name,
                "buyback_cost": buyback_cost,
                "base_cost": card.mana_cost or "",
                "resolved": True,
                "paid": paid,
            }
        })
        logger.info(
            "%s: AI resolved buyback for %s (cost: %s, paid: %s)",
            controller, card.name, buyback_cost, paid
        )
        return game_state

    def get_trigger_description(self) -> str:
        cost_str = self.cost or "{3}{B}"
        return f"Buyback {cost_str}: Pay to return this spell to your hand"
