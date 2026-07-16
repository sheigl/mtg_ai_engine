"""Storm keyword (CR 702.90a).

Storm is a triggered ability that copies the spell for each other spell
cast before it this turn. Copies are put on the stack in LIFO order so
they resolve first.
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)

_STORM_PATTERN = re.compile(r"\bstorm\b", re.IGNORECASE)


class Storm(TriggeredKeyword):
    """Storm keyword ability (CR 702.90a).

    When you cast this spell, copy it for each other spell that was cast
    before it this turn. You may choose new targets for the copies.
    """

    name = "storm"

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("storm" in k.lower() for k in keywords)
            or bool(_STORM_PATTERN.search(oracle))
        )

    @staticmethod
    def has_storm(keywords: list[str]) -> bool:
        """Check if a card has the Storm keyword by keyword list."""
        return "storm" in [k.lower() for k in keywords]

    @staticmethod
    def get_storm_count(game_state: GameState) -> int:
        """Get the number of spells cast this turn (for storm copy count)."""
        return getattr(game_state, "spells_cast_this_turn", 0)

    def apply(
        self,
        game_state: GameState,
        permanent: Permanent,
        target: Permanent | None = None,
    ) -> GameState:
        """Apply storm by creating copies on the stack.

        Creates N copies of the spell where N = spells_cast_this_turn - 1.
        Copies are added to the stack in LIFO order so they resolve first.

        Returns:
            New GameState with storm copies added to the stack.
        """
        return create_storm_copies(game_state, permanent.controller, permanent.id)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_STORM_PATTERN.search(oracle_text))


def create_storm_copies(gs: GameState, caster_name: str, stack_object_id: str) -> GameState:
    """Create storm copies of a spell on the stack (CR 702.90a).

    When you cast a spell with storm, copy it N times where N is the number
    of spells you've cast this turn minus one (the original spell counts as
    one). Copies are added to the stack in LIFO order so they resolve first.

    Args:
        gs: Current game state.
        caster_name: Name of the player who cast the storm spell.
        stack_object_id: The ID of the original storm spell on the stack.

    Returns:
        New GameState with N storm copies added to the stack.
    """
    import uuid as _uuid

    # Find the original spell on the stack by id
    source_obj = next(
        (o for o in gs.stack if o.id == stack_object_id), None,
    )
    if source_obj is None:
        logger.warning("Storm: stack object %r not found", stack_object_id)
        return gs.model_copy()

    # Storm count = spells cast this turn - 1 (original counts as one)
    storm_count = max(0, getattr(gs, "spells_cast_this_turn", 0) - 1)

    if storm_count == 0:
        logger.info("Storm: %s — no copies needed (only 1 spell cast this turn)", caster_name)
        return gs.model_copy()

    # Create N copies in LIFO order (last copy added = first to resolve)
    new_stack = list(gs.stack)
    for i in range(storm_count):
        copy_obj = source_obj.model_copy(update={
            "id": str(_uuid.uuid4()),
            "is_copy": True,
            "metadata": {**source_obj.metadata, "storm_copy_index": i},
        })
        new_stack.append(copy_obj)

    logger.info(
        "Storm: %s created %d copies of %s on stack",
        caster_name, storm_count, source_obj.source_card.name,
    )

    return gs.model_copy(update={"stack": new_stack})


def get_storm_count(gs: GameState) -> int:
    """Get the number of storm copies that would be created.

    Returns:
        Number of copies (spells_cast_this_turn - 1, minimum 0).
    """
    return max(0, getattr(gs, "spells_cast_this_turn", 0) - 1)
