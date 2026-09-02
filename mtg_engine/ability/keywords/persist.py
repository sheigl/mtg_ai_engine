"""Persist keyword ability (CR 702.61).

Persist is a triggered ability that functions when the creature with persist
dies. If it has no -1/-1 counters on it, its controller returns it to the
battlefield under their control with a -1/-1 counter on it.
"""
from __future__ import annotations
import logging
import re
import uuid
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent, PendingTrigger, StackObject

logger = logging.getLogger(__name__)

_PERSIST_PATTERN = re.compile(r"\bPersist\b", re.IGNORECASE)


class PersistKeyword(TriggeredKeyword):
    """Persist keyword ability.

    CR 702.61: "When a creature with persist dies, if it had no -1/-1 counters on it,
    return it to the battlefield under its owner's control with a -1/-1 counter on it."

    Persist is similar to Undying but returns the creature with a -1/-1 counter
    instead of +1/+1 counters equal to its power and toughness. A creature can only
    persist if it has no -1/-1 counters when it dies.
    """

    name = "persist"
    trigger_condition = "leaves_battlefield"

    def __init__(self, effect: str = ""):
        """Initialize Persist keyword.

        Args:
            effect: The effect text to apply on trigger.
        """
        self.effect = effect

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this card has Persist."""
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = any("persist" in k.lower() for k in keywords)
        has_oracle = bool(_PERSIST_PATTERN.search(oracle))
        return has_keyword or has_oracle

    @staticmethod
    def has_persist(keywords: list[str]) -> bool:
        """Check if a keyword list contains persist."""
        return any("persist" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains persist."""
        if not oracle_text:
            return False
        return bool(_PERSIST_PATTERN.search(oracle_text))

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply persist (no-op without death context)."""
        return game_state

    def resolve_trigger(
        self,
        game_state: "GameState",
        controller: str,
        card_name: str,
    ) -> "GameState":
        """Resolve persist trigger: return creature from graveyard with a -1/-1 counter.

        CR 702.61b: Return it to the battlefield under its owner's control with a -1/-1 counter on it.
        Pure transform: returns new GameState via model_copy.

        Args:
            game_state: Current game state.
            controller: Player who controlled the dying permanent.
            card_name: Name of the card in graveyard to return.

        Returns:
            New GameState with creature returned from graveyard.
        """
        from mtg_engine.engine.zones import get_player, put_permanent_onto_battlefield

        player = get_player(game_state, controller)

        # Find the card in graveyard (it should be there since it just died)
        target_card = next((c for c in player.graveyard if c.name == card_name), None)
        if target_card is None:
            logger.warning("Persist: %s not found in %s's graveyard", card_name, controller)
            return game_state

        # Remove from graveyard — pure transform via model_copy on player and players list
        new_graveyard = [c for c in player.graveyard if c.id != target_card.id]
        new_player = player.model_copy(update={"graveyard": new_graveyard})
        players = [new_player if p.name == controller else p for p in game_state.players]
        game_state = game_state.model_copy(update={"players": players})

        # Put onto battlefield with -1/-1 counter
        game_state, perm = put_permanent_onto_battlefield(
            game_state, target_card, controller, from_zone="graveyard"
        )
        if perm is not None:
            new_counters = dict(perm.counters) if perm.counters else {}
            new_counters["-1/-1"] = new_counters.get("-1/-1", 0) + 1
            battlefield = list(game_state.battlefield)
            for i, p in enumerate(battlefield):
                if p.id == perm.id:
                    battlefield[i] = p.model_copy(update={"counters": new_counters})
                    break
            game_state = game_state.model_copy(update={"battlefield": battlefield})

        logger.info("Persist: %s returned to battlefield with a -1/-1 counter", card_name)
        return game_state

    def create_trigger(
        self,
        game_state: "GameState",
        source_perm: "Permanent",
        leaving_perm: "Permanent",
        to_zone: str = "graveyard",
    ) -> "PendingTrigger | None":
        """Create trigger only if the dying creature has no -1/-1 counters.

        Args:
            game_state: Current game state.
            source_perm: The permanent with persist ability.
            leaving_perm: The permanent that left the battlefield.
            to_zone: Destination zone ("graveyard", "exile", etc.).

        Returns:
            PendingTrigger if conditions are met, None otherwise.
        """
        # Self-referential: only triggers for this specific creature
        if source_perm.id != leaving_perm.id:
            return None

        # Only triggers when going to graveyard ("dies")
        if to_zone != "graveyard":
            return None

        # Persist only fires if there are no -1/-1 counters
        counters = leaving_perm.counters or {}
        if counters.get("-1/-1", 0) > 0:
            logger.debug(
                "Persist on %s does not fire — already has -1/-1 counter(s)",
                leaving_perm.card.name,
            )
            return None

        from mtg_engine.models.game import PendingTrigger

        effect_text = self.effect or (
            f"Return {leaving_perm.card.name} to the battlefield with a -1/-1 counter."
        )
        return PendingTrigger(
            id=str(uuid.uuid4()),
            source_permanent_id=source_perm.id,
            controller=source_perm.controller,
            trigger_type="persist",
            effect_description=effect_text,
            source_card_name=source_perm.card.name,
            is_optional=False,
        )

    def get_trigger_description(self) -> str:
        return "Persist: When this dies with no -1/-1 counters, return it with a -1/-1 counter"


def resolve_trigger(game_state: "GameState", stack_obj: "StackObject") -> "GameState":
    """Resolve persist trigger from a StackObject.

    Delegates to PersistKeyword.resolve_trigger(). This is the primary entry point
    called by stack.py's dispatcher.

    Args:
        game_state: Current game state.
        stack_obj: The stack object containing trigger data.

    Returns:
        New GameState with creature returned from graveyard.
    """
    controller = stack_obj.controller
    card_name = stack_obj.source_card.name

    kw = PersistKeyword()
    return kw.resolve_trigger(game_state, controller, card_name)
