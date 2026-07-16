"""Cascade keyword (CR 702.85).

Cascade is a triggered ability that exiles cards from the top of the
library until a nonland card with lesser mana value is found, then
allows casting it without paying its mana cost. The remaining exiled
cards are put on the bottom in random order.
"""
from __future__ import annotations
import logging
import random
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)

_CASCADE_PATTERN = re.compile(r"\bcascade\b", re.IGNORECASE)


class Cascade(TriggeredKeyword):
    """Cascade keyword ability (CR 702.85).

    When you cast this spell, exile cards from the top of your library
    until you exile a nonland card that has lesser mana value than this
    spell's mana value. You may cast it without paying its mana cost.
    Then put all exiled cards that weren't cast on the bottom of your
    library in a random order.
    """

    name = "cascade"

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("cascade" in k.lower() for k in keywords)
            or bool(_CASCADE_PATTERN.search(oracle))
        )

    @staticmethod
    def has_cascade(keywords: list[str]) -> bool:
        """Check if a card has the Cascade keyword by keyword list."""
        return "cascade" in [k.lower() for k in keywords]

    def apply(
        self,
        game_state: GameState,
        permanent: Permanent,
        target: Permanent | None = None,
    ) -> GameState:
        """Apply cascade when the spell resolves.

        Exile cards from library top until finding a nonland card with
        strictly lower CMC than this spell's CMC. Queue pending_cascade
        for human players; auto-cast for AI.

        Returns:
            New GameState with cascade resolved or pending choice queued.
        """
        return apply_cascade(game_state, permanent.controller, self)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_CASCADE_PATTERN.search(oracle_text))


def apply_cascade(gs: GameState, caster_name: str, cascade_cmc: int | float = 3) -> GameState:
    """Apply the Cascade triggered ability (CR 702.85).

    Exile cards from the top of caster's library until a nonland card
    with CMC strictly less than *cascade_cmc* is found. You may cast that
    card without paying its mana cost. Then exile the other exiled cards
    on the bottom in random order.

    For **human** players: queues ``pending_cascade`` on GameState so the
    API layer can present a keep/exile choice.

    For **AI** players: auto-casts the found card (adds it to the stack as
    a free spell) and puts the remaining exiled cards on library bottom.

    Args:
        gs: Current game state.
        caster_name: Name of the player who cast the cascading spell.
        cascade_cmc: The CMC of the cascading spell (found card must have
            strictly lower CMC). Defaults to 3.

    Returns:
        New GameState with cascade resolved or pending choice queued.
    """
    from mtg_engine.engine.zones import get_player
    from mtg_engine.models.game import ExileStack, StackObject

    caster = get_player(gs, caster_name)
    if caster is None:
        logger.warning("Cascade: player %r not found", caster_name)
        return gs.model_copy()

    cascade_cmc = int(cascade_cmc)

    # --- Phase 1: exile cards until we find a valid card or library empties ---
    remaining_library: list = list(caster.library)
    exiled_non_chosen: list = []
    found_card = None

    while remaining_library:
        top_card = remaining_library.pop(0)
        type_lower = (top_card.type_line or "").lower()

        if "land" not in type_lower:
            card_cmc = int(top_card.cmc) if top_card.cmc is not None else 0
            if card_cmc < cascade_cmc:
                found_card = top_card
                break

        exiled_non_chosen.append(top_card)

    # --- Phase 2a: no valid card found — library emptied or all lands/high CMC ---
    if found_card is None:
        random.shuffle(exiled_non_chosen)
        new_library = exiled_non_chosen + remaining_library

        players_update = [
            p.model_copy(update={"library": new_library}) if p.name == caster_name else p
            for p in gs.players
        ]
        logger.info(
            "Cascade: %s — no card found with CMC < %d, exiled %d cards to bottom",
            caster_name, cascade_cmc, len(exiled_non_chosen),
        )
        return gs.model_copy(update={"players": players_update})

    # --- Phase 2b: valid card found ---
    exile_stack = ExileStack(reason="cascade", controller=caster_name, cards=exiled_non_chosen)

    new_player = caster.model_copy(update={"library": remaining_library})
    players_update = [
        new_player if p.name == caster_name else p for p in gs.players
    ]

    is_human = (
        getattr(gs, "human_player_name", None) is not None
        and caster_name == gs.human_player_name
    )

    if is_human:
        gs = gs.model_copy(update={
            "players": players_update,
            "exile_stacks": list(gs.exile_stacks) + [exile_stack],
            "pending_cascade": {
                "player": caster_name,
                "found_card": found_card.model_dump(),
                "found_card_id": found_card.id,
                "exiled_cards": [c.model_dump() for c in exiled_non_chosen],
                "cascade_cmc": cascade_cmc,
            },
        })
        logger.info(
            "Cascade: %s queued choice — found %s (CMC %d < %d)",
            caster_name, found_card.name, int(found_card.cmc or 0), cascade_cmc,
        )
    else:
        random.shuffle(exiled_non_chosen)
        new_library = exiled_non_chosen + remaining_library

        storm_copy = StackObject(
            source_card=found_card,
            controller=caster_name,
            is_copy=False,
            metadata={"cascade_cast": True},
        )

        gs = gs.model_copy(update={
            "players": [
                p.model_copy(update={"library": new_library}) if p.name == caster_name else p
                for p in gs.players
            ],
            "stack": list(gs.stack) + [storm_copy],
            "exile_stacks": [],
        })

        logger.info(
            "Cascade: %s auto-cast %s (CMC %d < %d), put %d cards on bottom",
            caster_name, found_card.name, int(found_card.cmc or 0), cascade_cmc,
            len(exiled_non_chosen),
        )

    return gs


def resolve_cascade_cast(gs: GameState) -> GameState:
    """Resolve the human player's choice to cast the cascading card."""
    pc = gs.pending_cascade
    if pc is None:
        return gs.model_copy()

    from mtg_engine.models.game import StackObject, Card as GameCard

    caster_name = pc["player"]
    found_card_dict = pc.get("found_card")
    exiled_cards_dicts = pc.get("exiled_cards", [])

    if not found_card_dict:
        return gs.model_copy(update={"pending_cascade": None})

    from mtg_engine.engine.zones import get_player

    caster = get_player(gs, caster_name)
    if caster is None:
        return gs.model_copy()

    found_card = GameCard(**found_card_dict)
    exiled_cards = [GameCard(**d) for d in exiled_cards_dicts]

    random.shuffle(exiled_cards)
    new_library = exiled_cards + list(caster.library)

    cascade_spell = StackObject(
        source_card=found_card,
        controller=caster_name,
        is_copy=False,
        metadata={"cascade_cast": True},
    )

    logger.info("Cascade resolved: %s casts %s for free", caster_name, found_card.name)

    return gs.model_copy(update={
        "pending_cascade": None,
        "players": [
            p.model_copy(update={"library": new_library}) if p.name == caster_name else p
            for p in gs.players
        ],
        "stack": list(gs.stack) + [cascade_spell],
    })


def resolve_cascade_exile(gs: GameState) -> GameState:
    """Resolve the human player's choice to exile the cascading card."""
    pc = gs.pending_cascade
    if pc is None:
        return gs.model_copy()

    from mtg_engine.models.game import Card as GameCard, ExileStack

    caster_name = pc["player"]
    found_card_dict = pc.get("found_card")
    exiled_cards_dicts = pc.get("exiled_cards", [])

    if not found_card_dict:
        return gs.model_copy(update={"pending_cascade": None})

    from mtg_engine.engine.zones import get_player

    caster = get_player(gs, caster_name)
    if caster is None:
        return gs.model_copy()

    found_card = GameCard(**found_card_dict)
    exiled_cards = [GameCard(**d) for d in exiled_cards_dicts]

    random.shuffle(exiled_cards)
    new_library = exiled_cards + list(caster.library)

    new_exile = list(caster.exile) + [found_card]
    exile_stack = ExileStack(reason="cascade", controller=caster_name, cards=[found_card])

    logger.info("Cascade resolved: %s exiles %s", caster_name, found_card.name)

    return gs.model_copy(update={
        "pending_cascade": None,
        "players": [
            p.model_copy(update={"library": new_library, "exile": new_exile})
            if p.name == caster_name else p
            for p in gs.players
        ],
        "exile_stacks": list(gs.exile_stacks) + [exile_stack],
    })
