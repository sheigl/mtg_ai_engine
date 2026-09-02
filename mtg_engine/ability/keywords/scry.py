"""Scry keyword action (CR 701.20 / sub-story CR 701.19).

``Scry N`` means "look at the top N cards of your library, then put any number
of them on the bottom of your library and the rest on top in any order."
(CR 701.19a) If there aren't enough cards to scry this way, the player looks at
as many as possible (CR 701.19b).

Library indexing convention throughout this module: index ``0`` is the *top* of
the library, so ``library[:n]`` are the N cards seen from top to bottom and a
reorder must keep that ordering — position 0 stays closest to the draw step.

The detection/parsing helpers were already present; this file implements a real
``apply()`` following the pure-transform pattern used by the other keyword modules:

* Meaningful changes return a **new** ``GameState`` built with
  ``model_copy(update={"players": [...]})`` — the controller's library list is
  rebuilt on a copy, never mutated in place.
* Every no-op path returns the **SAME** ``game_state`` object so callers can
  assert ``is gs`` and repeated events cannot double-fire (Q1/Q4).

Human vs AI:

* A human player (``game_state.human_player_name`` matches the acting controller)
  queues ``pending_scry_choice`` with the revealed cards and a reorder marker,
  returning **without** changing library order. The choice is resolved later via
  the ``scry`` handler in the API router (see :func:`resolve_scry_choice`).
* An AI player auto-resolves by estimating card quality from CMC + type:
  high-CMC non-lands are kept near the top, low-value lands are buried on the
  bottom. The reorder is applied through ``model_copy``; no valid cards to scry
  returns the SAME object.
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import KeywordAbility

if TYPE_CHECKING:
    from mtg_engine.models.game import Card, GameState, Permanent, PlayerState

logger = logging.getLogger(__name__)

# "Scry N" — the value is required for detection (a bare "Scry," still parses to 1).
_SCRY_PATTERN = re.compile(r"scry\s+(\d+)", re.IGNORECASE)

# effect_type marker used on ``pending_scry_choice`` to distinguish a regular
# Scry reorder from the reveal-and-choose / surge variants already handled in the
# API router. Kept as a module constant so both this module and game.py agree.
SCRY_EFFECT_TYPE = "scry"


class Scry(KeywordAbility):
    name = "scry"

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        return any("scry" in k.lower() for k in keywords)

    @staticmethod
    def has_scry(keywords: list[str]) -> bool:
        return any("scry" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_SCRY_PATTERN.search(oracle_text))

    @staticmethod
    def parse_scry_value(oracle_text: str) -> int:
        match = _SCRY_PATTERN.search(oracle_text or "")
        if match:
            return int(match.group(1))
        return 1

    def apply(
        self,
        game_state: GameState,
        permanent: Permanent,
        target: Permanent | None = None,
    ) -> GameState:
        """Apply a ``Scry N`` action (CR 701.20).

        The acting player is the Scry permanent's controller — they own the library
        being reordered (consistent with how Equip/Cycle derive the actor from
        ``permanent.controller``). An explicit ``player_name``/target overrides this,
        which lets a spell's scry effect be attributed to its caster.

        Guards (Q1/Q4):

        * No identifiable controller, or the controller is not in the game — strict
          no-op returning the **same** object.
        * ``n <= 0`` or an empty library — strict no-op returning the **same** object
          (scrying an empty library changes nothing).

        Human vs AI:

        * Human path queues ``pending_scry_choice`` with the revealed cards and
          returns **without** reordering the library.
        * AI path auto-resolves via :func:`_ai_reorder_library` using a pure
          ``model_copy`` transform.
        """
        # Derive acting player: explicit target wins, else permanent.controller.
        controller = _controller_from(permanent, target)
        if not controller:
            logger.debug(
                "Scry: %s has no identifiable controller; returning unchanged state",
                permanent.card.name,
            )
            return game_state

        player = _get_player(game_state, controller)
        if player is None:
            # Unknown / wrong controller — cannot scry anyone else's library.
            logger.debug(
                "Scry: %s not found for controller %s; returning unchanged state",
                permanent.card.name, controller,
            )
            return game_state

        n = self.parse_scry_value(permanent.card.oracle_text or "")
        if n <= 0:
            logger.debug("Scry: n<=0 for %s; returning unchanged state", permanent.card.name)
            return game_state

        library = list(player.library)
        # CR 701.19b: fewer than N cards => scry all remaining.
        k = min(n, len(library))
        if k == 0 or not library:
            logger.debug(
                "Scry: empty/short library for %s (%d card(s)); returning unchanged state",
                controller, len(library),
            )
            return game_state

        revealed = library[:k]

        # Human path: reveal the cards and queue a choice WITHOUT changing library
        # order. The human later reorders via the ``scry`` handler in the API router.
        if getattr(game_state, "human_player_name", None) == controller:
            new_state = game_state.model_copy(update={
                "pending_scry_choice": {
                    "player": controller,
                    "cards": list(revealed),  # Card objects, top -> bottom
                    "n": n,
                    "revealed_count": k,
                    "effect_type": SCRY_EFFECT_TYPE,
                }
            })
            logger.info(
                "Scry: queued reorder choice for %s to scry %d card(s) (requested %d)",
                controller, k, n,
            )
            return new_state

        # AI path: auto-resolve with a pure transform.
        gs = _ai_reorder_library(game_state, controller, revealed, library)
        logger.info(
            "Scry: %s AI reordered %d card(s); best on top",
            controller, k,
        )
        return gs


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _controller_from(permanent: Permanent, target: Permanent | None) -> str | None:
    """Return the acting player name.

    Prefers an explicit ``target`` (its controller); falls back to the permanent's
    own controller. Returns ``None`` when neither yields a usable name.
    """
    if target is not None:
        return getattr(target, "controller", None) or None
    return getattr(permanent, "controller", None) or None


def _get_player(game_state: GameState, name: str) -> "PlayerState | None":
    """Return the player with ``name`` or ``None`` (does not raise)."""
    for p in game_state.players:
        if p.name == name:
            return p
    return None


def _is_land(card: "Card") -> bool:
    """True if the card's type line indicates a land."""
    return "land" in (card.type_line or "").lower()


def _parse_card_cmc(card: "Card") -> float:
    """Return a card's CMC, preferring the ``cmc`` field and falling back to the
    mana cost. Returns ``0.0`` when neither is available."""
    cmc = getattr(card, "cmc", None)
    if cmc not in (None, ""):
        try:
            return float(cmc)
        except (TypeError, ValueError):
            pass
    from mtg_engine.engine.mana import parse_mana_cost as _parse_cost
    try:
        return float(_parse_cost(card.mana_cost or "").get("generic", 0))
    except Exception:  # pragma: no cover - defensive; mana parsing is best-effort
        return 0.0


def _score_scry_card(card: "Card") -> float:
    """Estimate how desirable a card is to keep near the TOP of the library.

    Matches the sub-story heuristic: high-CMC non-lands score highest (kept on
    top, drawn soonest); low-value lands sink to the bottom. Non-land scores equal
    their CMC (>= 0); land scores are always negative so every non-land outranks
    every land.
    """
    cmc = _parse_card_cmc(card)
    if _is_land(card):
        return -1.0
    return cmc


def _ai_reorder_library(
    game_state: GameState,
    controller: str,
    revealed: list["Card"],
    library: list["Card"],
) -> GameState:
    """Auto-resolve a Scry for an AI player (CR 701.20).

    Sorts the revealed cards so the best estimated card ends up on top (index 0,
    closest to the draw step) and the worst lands sink to the bottom, then rebuilds
    the controller's library with ``model_copy``. Pure transform: returns a new
    GameState with ``pending_scry_choice`` cleared.
    """
    ordered = sorted(revealed, key=_score_scry_card, reverse=True)
    new_library = list(ordered) + library[len(revealed):]

    player = _get_player(game_state, controller)
    if player is None:
        return game_state

    updated = player.model_copy(update={"library": new_library})
    new_players = [updated if p.name == controller else p for p in game_state.players]
    return game_state.model_copy(update={
        "players": new_players,
        "pending_scry_choice": None,
    })


def resolve_scry_choice(
    game_state: GameState,
    player_name: str,
    selection: object = None,
) -> GameState:
    """Resolve a human Scry reorder choice (CR 701.20).

    ``selection`` is the desired top-to-bottom ordering of the revealed cards,
    expressed either as an ordered list of card ids or (defensively) as a list of
    Card objects. The chosen permutation replaces ``library[:revealed_count]`` and
    the rest of the library stays put below it.

    Pure transform: returns a new GameState on success or the **same** object when
    there is no matching pending scry choice (Q4). An invalid / non-permutation
    selection simply clears the pending choice without reordering, so a stray
    submission cannot corrupt the library.
    """
    pending = getattr(game_state, "pending_scry_choice", None)
    if not pending or pending.get("player") != player_name:
        return game_state
    if pending.get("effect_type") != SCRY_EFFECT_TYPE:
        # Not a reorder scry (e.g. reveal-and-choose variant handled elsewhere).
        return game_state

    revealed = pending.get("cards", [])
    k = len(revealed)
    player = _get_player(game_state, player_name)
    if player is None or not player.library or k == 0:
        logger.debug(
            "Scry: clearing pending reorder for %s (no library / nothing revealed)",
            player_name,
        )
        return game_state.model_copy(update={"pending_scry_choice": None})

    wanted = _normalize_reorder(selection, revealed)
    if not _is_permutation(wanted, revealed):
        logger.debug(
            "Scry: invalid reorder selection for %s; clearing pending without reordering",
            player_name,
        )
        return game_state.model_copy(update={"pending_scry_choice": None})

    library = list(player.library)
    new_library = wanted + library[k:]
    updated = player.model_copy(update={"library": new_library})
    new_players = [updated if p.name == player_name else p for p in game_state.players]
    logger.info(
        "Scry: %s reordered %d card(s); resulting top is %s",
        player_name, k, new_library[0].name if new_library else "?",
    )
    return game_state.model_copy(update={
        "players": new_players,
        "pending_scry_choice": None,
    })


def _normalize_reorder(selection: object, revealed: list["Card"]) -> list["Card"]:
    """Coerce ``selection`` into an ordered list of Card objects (top -> bottom).

    Accepts either a list of card id strings or a list already holding Card
    objects. Anything else yields an empty list (treated as invalid by the caller).
    """
    if not isinstance(selection, (list, tuple)):
        return []

    ids = [c.get("id") if isinstance(c, dict) else c for c in selection]
    id_to_card = {c.id: c for c in revealed}
    result: list["Card"] = []
    for cid in ids:
        if isinstance(cid, dict):  # defensive: a full Card dict slipped through
            card = next((c for c in revealed if c.name == cid.get("name")), None)
            if card is not None:
                result.append(card)
            continue
        card = id_to_card.get(cid)
        if card is not None:
            result.append(card)
    return result


def _is_permutation(candidate: list["Card"], revealed: list["Card"]) -> bool:
    """True if ``candidate`` is a reordering of exactly the revealed cards."""
    if len(candidate) != len(revealed):
        return False
    try:
        return sorted(id(c) for c in candidate) == sorted(id(c) for c in revealed)
    except AttributeError:  # pragma: no cover - defensive
        return False


def apply_scry(game_state: GameState, permanent: Permanent, player_name: str | None = None) -> GameState:
    """Module-level convenience wrapper: ``Scry().apply(game_state, permanent)``."""
    return Scry().apply(game_state, permanent, target=None)
