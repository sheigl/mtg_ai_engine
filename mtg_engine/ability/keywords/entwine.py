"""Entwine keyword ability (CR 702.39).

Entwine {cost} is an additional cost that may be paid as a multimode spell
is cast. If you pay the entwine cost, you choose all modes of the spell.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_ENTWINE_PATTERN = re.compile(r"\bEntwine\b\s+(?P<cost>(?:\{[^}]+\})+)", re.IGNORECASE)
_ENTWINE_PLAIN = re.compile(r"\bEntwine\b", re.IGNORECASE)


class EntwineKeyword(CostKeyword):
    """Entwine keyword ability.

    CR 702.39: "Entwine {cost}" is an additional cost that may be paid as a
    multimode spell is cast. If you pay the entwine cost, you choose all modes
    of the spell instead of just one.

    Example: "Entwine {2}{U}" — Pay {2}{U} to choose both modes.
    """

    name = "entwine"

    def __init__(self, cost: str | None = None):
        """Initialize Entwine keyword.

        Args:
            cost: The additional mana cost for entwining (e.g., "{2}{U}").
        """
        self.cost = cost

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Entwine."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("entwine" in k.lower() for k in keywords)
        has_oracle = bool(_ENTWINE_PLAIN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_entwine(keywords: list[str]) -> bool:
        """Check if a keyword list contains entwine."""
        return any("entwine" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains entwine."""
        if not oracle_text:
            return False
        return bool(_ENTWINE_PLAIN.search(oracle_text))

    @staticmethod
    def parse_entwine_cost(oracle_text: str) -> str | None:
        """Parse the entwine cost from oracle text.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            Cost string (e.g., "{2}{U}") or None if not found.
        """
        match = _ENTWINE_PATTERN.search(oracle_text or "")
        if match:
            return match.group("cost").strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "EntwineKeyword | None":
        """Create EntwineKeyword from oracle text if present.

        Args:
            oracle_text: The card's oracle text.

        Returns:
            EntwineKeyword if entwine is found, None otherwise.
        """
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_entwine_cost(oracle_text))
        return None

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply entwine (CR 702.39).

        Entwine {cost} is an ADDITIONAL cost that may be paid as a modal spell
        is cast. If paid, all modes are chosen instead of just one.

        Called during spell declaration (the card controller is the caster and
        ``permanent`` is the spell in hand being cast).

        - Human caster: queues ``pending_entwine_choice`` on the GameState
          (resolved=False). The cast is deferred until the ``entwine_pay`` /
          ``entwine_pass`` choice handler re-drives it.
        - AI caster: auto-resolves — ``pending_entwine_choice`` is set with
          resolved=True and ``paid=True`` iff the pool can cover base cost +
          entwine cost. The actual deduction happens in ``cast_spell``.
        - No-op (returns SAME game_state object): card has no entwine, no
          parseable entwine cost, or the card is not modal (mode count <= 1).

        Returns:
            Modified game state with ``pending_entwine_choice`` set, or the
            same object on no-op.
        """
        from mtg_engine.engine.mana import can_pay_cost
        from mtg_engine.engine.zones import get_player
        from mtg_engine.engine.stack import _split_modal_texts

        card = permanent.card
        oracle_text = card.oracle_text or ""

        # No-op guard 1: card must have entwine
        if not (
            self.has_entwine(card.keywords or [])
            or bool(_ENTWINE_PLAIN.search(oracle_text))
        ):
            return game_state

        # No-op guard 2: parseable entwine cost required
        entwine_cost = self.parse_entwine_cost(oracle_text)
        if not entwine_cost:
            return game_state

        # No-op guard 3: entwine only applies to modal spells
        modes = _split_modal_texts(oracle_text)
        if len(modes) <= 1:
            return game_state

        controller = permanent.controller

        # Human vs AI
        is_human = (
            getattr(game_state, "human_player_name", None) is not None
            and controller == game_state.human_player_name
        )

        if is_human:
            game_state = game_state.model_copy(update={
                "pending_entwine_choice": {
                    "player": controller,
                    "card_id": card.id,
                    "card_name": card.name,
                    "entwine_cost": entwine_cost,
                    "base_cost": card.mana_cost or "",
                    "num_modes": len(modes),
                    "resolved": False,
                    "paid": False,
                }
            })
            logger.info(
                "%s: queued entwine choice for %s (cost: %s, modes: %d)",
                controller, card.name, entwine_cost, len(modes)
            )
            return game_state

        # AI auto-resolution
        player = get_player(game_state, controller)
        if player is None:
            logger.warning("Player not found for entwine resolution: %s", controller)
            return game_state

        combined_cost = (card.mana_cost or "") + entwine_cost
        paid = can_pay_cost(player.mana_pool, combined_cost)

        game_state = game_state.model_copy(update={
            "pending_entwine_choice": {
                "player": controller,
                "card_id": card.id,
                "card_name": card.name,
                "entwine_cost": entwine_cost,
                "base_cost": card.mana_cost or "",
                "num_modes": len(modes),
                "resolved": True,
                "paid": paid,
            }
        })
        logger.info(
            "%s: AI resolved entwine for %s (cost: %s, paid: %s)",
            controller, card.name, entwine_cost, paid
        )
        return game_state

    def get_trigger_description(self) -> str:
        cost_str = self.cost or "{2}{U}"
        return f"Entwine {cost_str}: Pay to choose all modes"
