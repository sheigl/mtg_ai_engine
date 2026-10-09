"""Phasing keyword (CR 702.26).

``Phasing`` is a passive, static mechanic: at the end of the controller's untap
step that player's permanents with phasing phase out; at the start of that same
player's *next* untap step they phase back in. While phased out a permanent is
treated as though it doesn't exist (CR 702.26a) — it can't be targeted, attacked
with against, blocked, or affected by anything — but it keeps its counters and any
attached Auras/Equipment phase out with it and stay attached on return.

This module implements the two state transitions as **pure transforms**:

* ``phase_out(game_state, controller)`` returns a *new* ``GameState`` (via
  ``model_copy``) in which every one of ``controller``'s phasing permanents that
  is not already phased out becomes phased out and is recorded in
  ``phased_out_permanents`` / ``phased_out_turns``.
* ``phase_in(game_state, controller)`` returns a *new* ``GameState`` in which every
  permanent currently phased out under ``controller`` phases back in (its
  ``phased_out`` flag is cleared and it drops out of ``phased_out_permanents``).

No-op discipline (Q4): the no-op guard on both functions returns the **same**
``game_state`` object when nothing qualifies, so repeated events cannot double-fire
and callers can assert ``is gs``.

Driving hooks live in ``turn_manager.py`` (phase-in at the start of the untap
step, phase-out at the end). Targeting / combat / SBA exclusion is handled via the
shared :func:`is_phased_out` helper in ``stack.py``, ``combat/core.py`` and
``sba.py``.
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import PassiveKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState

logger = logging.getLogger(__name__)

# Detection regex — a bare "Phasing" keyword reminder still counts (CR 702.26).
_PHASING_RE = re.compile(r"\bphasing\b", re.IGNORECASE)


class PhasingKeyword(PassiveKeyword):
    """Passive end-of-untap phase-out / start-of-next-untap phase-in."""

    name = "phasing"

    @staticmethod
    def has_phasing(card_or_perm) -> bool:
        """Return True if ``card_or_perm`` has the Phasing keyword.

        Accepts either a ``Card``/``Permanent`` (reads ``.card.keywords`` /
        ``.keywords`` or oracle text) or a raw list of keyword strings.
        """
        keywords: list[str] = []
        oracle_text: str = ""
        card = getattr(card_or_perm, "card", None)
        if card is not None:
            keywords = card.keywords or []
            oracle_text = card.oracle_text or ""
        elif isinstance(card_or_perm, (list, tuple)):
            keywords = list(card_or_perm)
        else:
            # Assume a bare iterable of keyword strings was passed directly.
            keywords = [str(k) for k in card_or_perm]

        if any("phasing" in str(k).lower() for k in keywords):
            return True
        return bool(_PHASING_RE.search(oracle_text))

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """True when the oracle text contains a ``Phasing`` keyword reminder."""
        if not oracle_text:
            return False
        return bool(_PHASING_RE.search(oracle_text))


# ---------------------------------------------------------------------------
# Module-level helpers (mirrors crew.py / scry.py patterns)
# ---------------------------------------------------------------------------

def is_phased_out(game_state: GameState, perm_id: str) -> bool:
    """True if the permanent ``perm_id`` is currently phased out.

    Shared by ``stack.py``, ``combat/core.py`` and ``sba.py`` so every call site
    uses a single source of truth. Looks the permanent up on the battlefield (a
    phased-out object stays in its zone) and inspects the ``phased_out`` flag;
    falls back to the ``phased_out_permanents`` registry when the permanent isn't
    found (e.g. during construction). Returns False for an unknown id.
    """
    perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if perm is not None:
        return bool(getattr(perm, "phased_out", False))
    # Fallback: the permanent may be missing from the battlefield list but still
    # recorded as phased out (defensive; normal flow keeps it in the list).
    return perm_id in game_state.phased_out_permanents


def _controller_has_phasing(game_state: GameState, controller: str) -> bool:
    """True if any of ``controller``'s battlefield permanents has phasing."""
    for perm in game_state.battlefield:
        if perm.controller == controller and PhasingKeyword.has_phasing(perm):
            return True
    return False


def phase_out(
    game_state: GameState,
    controller_name: str,
    skip_ids: "set[str] | frozenset[str] | None" = None,
) -> GameState:
    """Phase out every one of ``controller_name``'s phasing permanents (CR 702.26b).

    Pure transform: returns a *new* ``GameState`` where each qualifying permanent's
    ``phased_out`` flag is set to True, its controller's entry recorded in
    ``phased_out_permanents``, and the current turn recorded in
    ``phased_out_turns``. Returns the **same** object when nothing qualifies (no
    phasing permanents owned by this controller) — Q4 no-op guard.

    ``skip_ids`` is an optional collection of permanent ids that must NOT be phased
    out on this call. ``turn_manager.py`` passes the ids that were just returned by
    :func:`phase_in` in the *same* untap step so a permanent coming back does not
    immediately phase out again at the end of that same step (CR 702.26 ordering:
    phase-in at start, phase-out at end — a returning permanent survives the turn).
    """
    skip_ids = skip_ids or set()

    if not _controller_has_phasing(game_state, controller_name):
        logger.debug(
            "Phase-out: %s has no phasing permanents; returning unchanged state",
            controller_name,
        )
        return game_state

    new_battlefield = []
    phased_out_permanents = dict(game_state.phased_out_permanents)
    phased_out_turns = dict(game_state.phased_out_turns)
    changed = False

    for perm in game_state.battlefield:
        if (
            perm.controller == controller_name
            and PhasingKeyword.has_phasing(perm)
            and not getattr(perm, "phased_out", False)
            and perm.id not in skip_ids
        ):
            new_perm = perm.model_copy(update={"phased_out": True})
            phased_out_permanents[new_perm.id] = controller_name
            phased_out_turns[new_perm.id] = game_state.turn
            new_battlefield.append(new_perm)
            changed = True
            logger.info(
                "Phasing: %s (controller %s) phases out at turn %d",
                perm.card.name, controller_name, game_state.turn,
            )
        else:
            new_battlefield.append(perm)

    if not changed:
        # Nothing newly qualified — keep the SAME object so callers can assert `is`.
        return game_state

    gs = game_state.model_copy(update={
        "battlefield": new_battlefield,
        "phased_out_permanents": phased_out_permanents,
        "phased_out_turns": phased_out_turns,
    })
    logger.info("Phasing: %s phases out (turn %d)", controller_name, game_state.turn)
    return gs


def phase_in(game_state: GameState, controller_name: str) -> GameState:
    """Phase back in every one of ``controller_name``'s currently-phased-out permanents.

    Pure transform: returns a *new* ``GameState`` with each qualifying permanent's
    ``phased_out`` flag cleared and its entry removed from
    ``phased_out_permanents`` / ``phased_out_turns``. Returns the **same** object
    when this controller has nothing phased out — Q4 no-op guard.

    Note: this call does NOT fire an untap event and does NOT reset summoning
    sickness (per CR 702.26 the permanent enters the turn already "untapped"). The
    untap loop in ``turn_manager.py`` handles untapping normally.
    """
    my_ids = [pid for pid, ctrl in game_state.phased_out_permanents.items() if ctrl == controller_name]
    if not my_ids:
        logger.debug(
            "Phase-in: %s has no phased-out permanents; returning unchanged state",
            controller_name,
        )
        return game_state

    new_battlefield = []
    changed = False
    for perm in game_state.battlefield:
        if perm.id in my_ids:
            new_perm = perm.model_copy(update={"phased_out": False})
            new_battlefield.append(new_perm)
            changed = True
            logger.info(
                "Phasing: %s (controller %s) phases back in at turn %d",
                perm.card.name, controller_name, game_state.turn,
            )
        else:
            new_battlefield.append(perm)

    if not changed:
        return game_state

    remaining = {pid: ctrl for pid, ctrl in game_state.phased_out_permanents.items()
                 if ctrl != controller_name}
    gs = game_state.model_copy(update={
        "battlefield": new_battlefield,
        "phased_out_permanents": remaining,
        "phased_out_turns": {pid: t for pid, t in game_state.phased_out_turns.items()
                             if pid not in my_ids},
    })
    logger.info("Phasing: %d permanent(s) of %s phased back in", len(my_ids), controller_name)
    return gs
