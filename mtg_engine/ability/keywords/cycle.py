"""Cycling & Type Cycling keyword abilities (CR 702.36, CR 702.46).

Regular cycling ``"{cost}, Discard this card: Draw a card."`` is an activated
ability (CR 702.36/702.28a). Type cycling ``"{cost}, Discard this card: Draw X
cards"`` draws X = the number of card *types* on the card (CR 702.46b). Both
variants resolve from the HAND (not the battlefield) and are implemented as
pure transforms (``model_copy(update={...})``) — never mutating a live player.

The two keywords must coexist: a card carries either regular cycling or type
cycling, and each detector rejects the other. Regular cycling's pattern uses a
negative lookbehind so ``"Type cycling {2}"`` is NOT parsed as regular cycling,
and a word-boundary guard so basic-land-cycling tokens (``"Swampcycling {2}"``,
preceded by a letter) are not mistaken for regular cycling either.
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword, TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Card, Permanent, PlayerState

logger = logging.getLogger(__name__)

# --- Regular cycling (CR 702.36) -------------------------------------------
# Match a bare "Cycling {cost}" but reject "Type cycling {cost}" and basic-land
# cycling tokens ("Swampcycling", ...). The ``(?<!\w)`` guard keeps the leading
# word boundary; the ``(?<!type )`` guard rejects type-cycling.
_CYCLING_PATTERN = re.compile(
    r"(?<!\w)(?<!type )cycling\s*(\{[^}]+\})",
    re.IGNORECASE,
)

# --- Type cycling (CR 702.46) ----------------------------------------------
_TYPECYCLING_PATTERN = re.compile(r"type\s+cycling\s*(\{[^}]+\})", re.IGNORECASE)

# Core card types per CR 304 / 702.46b — only these count toward X for type
# cycling. Supertypes (Legendary, Basic, Snow, ...) and subtypes are ignored.
_CARD_TYPES = {"land", "creature", "instant", "sorcery", "artifact", "planeswalker", "tribal"}


# ---------------------------------------------------------------------------
# Regular Cycling (CR 702.36)
# ---------------------------------------------------------------------------

class CyclingKeyword(CostKeyword):
    """Regular cycling — "{cost}, Discard this card: Draw a card."

    An activated ability (not triggered) that resolves from the hand. For a human
    player the acting controller queues ``pending_cycling_choice`` and nothing is
    discarded or drawn yet; the choice is later resolved via the ``cycling``
    handler in the API router. For an AI player the ability auto-resolves by
    paying the cost (if affordable) then discarding the card and drawing one card.

    State transforms are pure: meaningful changes return a new GameState built
    with ``model_copy(update={...})``; every no-op path returns the SAME object
    so callers can assert ``is gs`` (Q4).
    """

    name = "cycling"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    @staticmethod
    def has_cycling(keywords: list[str]) -> bool:
        """True if the keyword list carries *regular* cycling (not type-cycling)."""
        for k in keywords or []:
            lk = k.lower()
            if "cycling" in lk and not lk.startswith("type"):
                return True
        return False

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """True if ``oracle_text`` carries regular cycling (not type-cycling)."""
        if not oracle_text:
            return False
        return bool(_CYCLING_PATTERN.search(oracle_text))

    @staticmethod
    def parse_cost(oracle_text: str) -> str | None:
        match = _CYCLING_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "CyclingKeyword | None":
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_cost(oracle_text))
        return None

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return self.from_oracle_text(oracle) or self.has_cycling(keywords)

    def apply(
        self,
        game_state: GameState,
        card_or_permanent: "Card | Permanent",
        player_name: str | None = None,
    ) -> GameState:
        """Activate regular cycling (CR 702.36). Accepts a Card or Permanent."""
        from mtg_engine.models.game import Permanent as _Permanent

        if isinstance(card_or_permanent, _Permanent):
            perm = card_or_permanent
            card = perm.card
            controller = perm.controller
        else:
            card = card_or_permanent
            controller = player_name

        oracle_text = card.oracle_text or ""

        # Guard (Q1): only cards that actually carry *regular* cycling are
        # processed. Anything else (incl. type-cycling) is a strict no-op
        # returning the SAME object so repeated events cannot double-fire.
        if not self.from_oracle_text(oracle_text):
            logger.debug("Cycling: %s has no regular cycling keyword, returning unchanged state", card.name)
            return game_state

        cost = self.cost or self.parse_cost(oracle_text) or "{1}"
        return _resolve_cycle(game_state, card, controller, draw_count=1, cost=cost)


# ---------------------------------------------------------------------------
# Type Cycling (CR 702.46)
# ---------------------------------------------------------------------------

class TypeCyclingKeyword(TriggeredKeyword):
    """Type cycling — "{cost}, Discard this card: Draw X cards" where X is the
    number of card *types* on this card (CR 702.46b).

    Like regular cycling this is an activated ability resolving from the hand;
    only the draw count differs (X = core card types, not supertypes/subtypes).
    """

    name = "typecycling"

    def __init__(self, base_cost: str = "", base_draw: int = 1):
        self.base_cost = base_cost
        self.base_draw = base_draw

    @staticmethod
    def has_type_cycling(keywords: list[str]) -> bool:
        return any(k.lower().startswith("type") and "cycling" in k.lower() for k in keywords or [])

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        has_keyword = self.has_type_cycling(keywords)
        has_oracle = bool(_TYPECYCLING_PATTERN.search(oracle))
        return has_keyword or has_oracle

    def get_card_type_count(self, card: "Card") -> int:
        """Count the number of *card types* on the card (CR 702.46b).

        Only core card types (Land / Creature / Instant / Sorcery / Artifact /
        Planeswalker / Tribal) count. Supertypes (Legendary, Basic, Snow, ...)
        and subtypes are ignored, so ``"Creature — Elf Warrior"`` == 1 while
        ``"Instant — Sorcery"`` == 2.
        """
        type_line = card.type_line or ""
        if not type_line:
            return 1

        count = sum(
            1
            for token in type_line.replace("—", " ").replace("-", " ").split()
            if token.lower() in _CARD_TYPES
        )
        return max(1, count)

    def get_draw_count(self, card: "Card") -> int:
        """Number of cards to draw when type-cycling ``card`` (>= 1)."""
        return self.get_card_type_count(card)

    def type_cycle(
        self,
        game_state: GameState,
        card: "Card",
        controller_name: str,
    ) -> "GameState":
        """Execute type cycling: pay nothing, discard and draw X cards (pure).

        Pure transform: returns a new GameState built with ``model_copy``. The
        previous implementation mutated the live player lists in place; it now
        rebuilds hand/graveyard/library on copies only when the card is actually
        present in the controller's hand, otherwise it returns the SAME object.
        """
        draw_count = self.get_draw_count(card)
        controller = _get_player(game_state, controller_name)

        # No-op (return same object) if the player or card cannot be found.
        if controller is None or not any(c.id == card.id for c in controller.hand):
            logger.debug("TypeCycling: %s not in hand of %s, returning unchanged state", card.name, controller_name)
            return game_state

        gs = _discard_and_draw(game_state, controller_name, card, draw_count)
        logger.info(
            "%s type-cycled %s (types: %d) and drew %d cards",
            controller_name,
            card.name,
            self.get_card_type_count(card),
            draw_count,
        )
        return gs

    def apply(
        self,
        game_state: GameState,
        card_or_permanent: "Card | Permanent",
        player_name: str | None = None,
    ) -> GameState:
        """Activate type cycling (CR 702.46). Accepts a Card or Permanent."""
        from mtg_engine.models.game import Permanent as _Permanent

        if isinstance(card_or_permanent, _Permanent):
            perm = card_or_permanent
            card = perm.card
            controller = perm.controller
        else:
            card = card_or_permanent
            controller = player_name

        oracle_text = card.oracle_text or ""

        # Guard (Q1): only cards that actually carry type-cycling are processed.
        if not self.applies(game_state, _as_perm(card)):
            logger.debug("TypeCycling: %s has no type-cycling keyword, returning unchanged state", card.name)
            return game_state

        cost = self.base_cost or TypeCyclingKeyword.parse_cost(oracle_text) or "{1}"
        draw_count = max(1, self.get_draw_count(card))
        return _resolve_cycle(game_state, card, controller, draw_count=draw_count, cost=cost)

    def get_trigger_description(self) -> str:
        return f"Type cycling {self.base_cost}: Draw cards = number of types"

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "TypeCyclingKeyword | None":
        """Create TypeCyclingKeyword from oracle text if present."""
        match = _TYPECYCLING_PATTERN.search(oracle_text or "")
        if match:
            return cls(base_cost=match.group(1))
        return None

    @staticmethod
    def parse_cost(oracle_text: str) -> str | None:
        match = _TYPECYCLING_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None


# ---------------------------------------------------------------------------
# Module-level helpers (shared by both variants)
# ---------------------------------------------------------------------------

def _get_player(game_state: GameState, name: str) -> "PlayerState | None":
    """Return the player with ``name`` or ``None`` (does not raise)."""
    for p in game_state.players:
        if p.name == name:
            return p
    return None


def _as_perm(card: "Card") -> "Permanent":
    """Build a throw-away Permanent wrapping ``card`` for keyword queries."""
    from mtg_engine.models.game import Permanent
    return Permanent(card=card, controller="")


def _resolve_cycle(
    game_state: GameState,
    card: "Card",
    controller: str | None,
    draw_count: int,
    cost: str,
) -> GameState:
    """Shared resolve for regular/type cycling.

    Guards (Q1/Q4): the acting player must exist, the card must be in their hand
    (cycling resolves from hand), and they must hold priority; any violation is a
    strict no-op returning the SAME object so repeated events cannot double-fire.

    Human path: queue ``pending_cycling_choice`` WITHOUT paying/discarding/
    drawing. AI path: pay the cost if affordable (else pure no-op returning the
    same object), then discard and draw up to ``draw_count`` cards from the top
    of the library.
    """
    if controller is None:
        return game_state

    player = _get_player(game_state, controller)
    if player is None or not any(c.id == card.id for c in player.hand):
        logger.debug(
            "Cycling: %s (%s) not in hand of %s, returning unchanged state",
            card.name, card.id, controller,
        )
        return game_state

    # You can only activate abilities you have priority for.
    if game_state.priority_holder != controller:
        logger.debug(
            "Cycling: %s not activated while %s holds priority, returning unchanged state",
            card.name, game_state.priority_holder,
        )
        return game_state

    is_human = (
        getattr(game_state, "human_player_name", None) is not None
        and controller == game_state.human_player_name
    )

    if is_human:
        new_state = game_state.model_copy(update={
            "pending_cycling_choice": {
                "player": controller,
                "card_id": card.id,
                "card_name": card.name,
                "cost": cost,
                "draw_count": draw_count,
                "resolved": False,
            }
        })
        logger.info(
            "Cycling: queued choice for %s to cycle %s (cost %s, draw %d)",
            controller, card.name, cost, draw_count,
        )
        return new_state

    # AI path: pay if affordable, else pure no-op returning the SAME object.
    from mtg_engine.engine.mana import can_pay_cost

    if not can_pay_cost(player.mana_pool, cost):
        logger.debug(
            "Cycling: %s AI cannot afford %s for %s, returning unchanged state",
            card.name, cost, controller,
        )
        return game_state

    gs = _pay_mana(game_state, controller, cost)
    player = _get_player(gs, controller) or player
    return _discard_and_draw(gs, controller, card, draw_count)


def _pay_mana(game_state: GameState, controller_name: str, cost: str) -> GameState:
    """Deduct ``cost`` from the controller's mana pool (pure transform).

    Mirrors the kicker/flashback payment order: colored slots first, then
    generic/colorless. Returns the SAME object when nothing is deducted.
    """
    player = _get_player(game_state, controller_name)
    if player is None:
        return game_state

    from mtg_engine.engine.mana import parse_mana_cost as _parse_cost

    pool = player.mana_pool
    cost_dict = _parse_cost(cost or "")
    new_slots = {
        "W": pool.W, "U": pool.U, "B": pool.B,
        "R": pool.R, "G": pool.G, "C": pool.C,
    }
    remaining = dict(cost_dict)

    # Colored requirements first.
    for color in ("W", "U", "B", "R", "G"):
        need = remaining.get(color, 0)
        if need and new_slots[color] >= need:
            new_slots[color] -= need
            remaining[color] = 0

    # Generic + explicit {C} from colorless first, then leftover colored.
    generic_needed = remaining.get("generic", 0) + remaining.get("C", 0)
    if generic_needed > 0:
        if new_slots["C"] >= generic_needed:
            new_slots["C"] -= generic_needed
        else:
            leftover = generic_needed - new_slots["C"]
            new_slots["C"] = 0
            for c in ("W", "U", "B", "R", "G"):
                if leftover <= 0:
                    break
                take = min(new_slots[c], leftover)
                new_slots[c] -= take
                leftover -= take

    payment = {
        c: new_slots[c]
        for c in ("W", "U", "B", "R", "G", "C")
        if new_slots[c] != getattr(pool, c, 0)
    }
    if not payment:
        return game_state

    updated = player.model_copy(update={"mana_pool": pool.model_copy(update=payment)})
    new_players = [
        updated if p.name == controller_name else p for p in game_state.players
    ]
    return game_state.model_copy(update={"players": new_players})


def _discard_and_draw(
    game_state: GameState,
    controller_name: str,
    card: "Card",
    draw_count: int,
) -> GameState:
    """Discard ``card`` to graveyard; draw up to ``draw_count`` from library top.

    Pure transform: rebuilds the controller's hand/graveyard/library on copies and
    returns a new GameState. Library index 0 is the top, so the first ``draw_count``
    cards are drawn (fewer if the library is short). The card is removed by id to
    match the engine's canonical discard convention.
    """
    new_players = []
    for p in game_state.players:
        if p.name != controller_name:
            new_players.append(p)
            continue

        hand = [c for c in p.hand if c.id != card.id]
        graveyard = list(p.graveyard) + [card]
        library = list(p.library)
        taken = min(draw_count, len(library))
        drawn = library[:taken]
        library = library[taken:]
        hand = hand + drawn

        new_players.append(
            p.model_copy(update={"hand": hand, "graveyard": graveyard, "library": library})
        )

    return game_state.model_copy(update={"players": new_players})


def resolve_cycling_choice(game_state: GameState, player_name: str) -> GameState:
    """Resolve a human Cycling choice (CR 702.36 / 702.46).

    Pays the queued cost from the controller's mana pool, discards the card and
    draws ``draw_count`` cards, then clears ``pending_cycling_choice``. Used by
    the API router's ``cycling`` choice handler. Pure transform: returns a new
    GameState on success or the SAME object when there is no matching pending
    choice (Q4).
    """
    pending = getattr(game_state, "pending_cycling_choice", None)
    if not pending or pending.get("player") != player_name:
        return game_state

    card_id = pending.get("card_id")
    draw_count = int(pending.get("draw_count", 1))
    cost = pending.get("cost", "{1}")

    player = _get_player(game_state, player_name)
    if player is None or not any(c.id == card_id for c in player.hand):
        logger.debug(
            "Cycling: %s has no matching cycling card in hand; clearing pending",
            player_name,
        )
        return game_state.model_copy(update={"pending_cycling_choice": None})

    gs = _pay_mana(game_state, player_name, cost)
    card = next(
        (c for p in gs.players for c in p.hand if c.id == card_id), None
    )
    if card is None:
        return gs.model_copy(update={"pending_cycling_choice": None})

    gs = _discard_and_draw(gs, player_name, card, draw_count)
    logger.info(
        "Cycling: %s resolved cycling of %s (cost %s, drew %d)",
        player_name, card.name, cost, draw_count,
    )
    return gs.model_copy(update={"pending_cycling_choice": None})


def apply_cycling(game_state: GameState, card_or_permanent, player_name: str | None = None) -> GameState:
    """Module-level convenience wrapper for regular cycling."""
    return CyclingKeyword().apply(game_state, card_or_permanent, player_name)


def apply_type_cycling(
    game_state: GameState, card_or_permanent, player_name: str | None = None
) -> GameState:
    """Module-level convenience wrapper for type cycling."""
    return TypeCyclingKeyword().apply(game_state, card_or_permanent, player_name)
