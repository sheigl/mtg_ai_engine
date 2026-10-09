"""Saddle keyword (Bloomburrow, BLI 2025).

"Saddle — This enters the battlefield attached to target creature you control,
as an Equipment would."

Saddle behaves like Equip but triggers at enter-the-battlefield rather than via
an activated ability: when the saddled spell resolves, the permanent enters the
battlefield already attached to a target creature the controller controls. There
is NO activated ability, NO sorcery-speed gate, and NO mana/tap cost — Saddle is
part of the spell resolving (no published CR number yet; Bloomburrow is brand new).

This module reuses the mature attachment infrastructure in ``stack.py``:
``_apply_equip`` sets ``permanent.attached_to``, updates the host's
``attachments`` list and fires attach triggers — exactly what Saddle needs, just
triggered at ETB instead of via an activated Equip ability.
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)

# Saddle is a bare keyword reminder (no cost to parse); detect the word itself.
_SADDLE_RE = re.compile(r"\bsaddle\b", re.IGNORECASE)


class SaddleKeyword(CostKeyword):
    """The Saddle keyword: attach to a creature you control at ETB."""

    name = "saddle"

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        return self.from_oracle_text(permanent.card.oracle_text or "")

    @staticmethod
    def has_saddle(card_or_perm) -> bool:
        """Detect Saddle on a ``Card``/``Permanent`` (or raw oracle-text string)."""
        if hasattr(card_or_perm, "card"):
            oracle = card_or_perm.card.oracle_text or ""
        else:
            oracle = str(card_or_perm or "")
        return SaddleKeyword.from_oracle_text(oracle)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_SADDLE_RE.search(oracle_text))

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        """Detect Saddle on ``permanent`` and resolve the ETB attachment.

        Human path (controller holds priority / is human): queue
        ``pending_saddle_choice`` with the list of eligible creatures WITHOUT
        attaching — the permanent stays loose on the battlefield until resolved via
        the ``saddle_confirm`` choice handler in the API router.

        AI path: attach to the highest-power eligible creature the controller
        controls (deterministic tie-break by ascending permanent id) via the shared
        ``_apply_equip`` helper. No eligible creature => pure no-op returning the
        SAME object (Q4). Non-saddled permanents are a strict no-op too.

        State transforms are pure: meaningful changes return a new GameState built
        with ``model_copy(update={...})``; every no-op path returns the SAME object
        so callers can assert ``is gs`` (Q4).
        """
        return apply_saddle(game_state, permanent.id)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _creature_power(perm: Permanent) -> int:
    """Return the base power of a creature permanent (0 if unparseable)."""
    try:
        return max(0, int(perm.card.power or "0"))
    except (ValueError, TypeError):
        return 0


def _is_creature_perm(perm: Permanent) -> bool:
    """True if the permanent's type line indicates a creature."""
    return "creature" in (perm.card.type_line or "").lower()


def _eligible_creatures(game_state: GameState, controller: str) -> list[Permanent]:
    """Return creatures the ``controller`` controls on the battlefield.

    Tokens count — they are creatures and therefore legal Saddle targets (CR 702.XX).
    This is the set of legal attachment targets: any creature you control. The
    caller is responsible for any additional filtering (e.g. already-attached).
    """
    return [
        perm
        for perm in game_state.battlefield
        if perm.controller == controller and _is_creature_perm(perm)
    ]


def apply_saddle(game_state: GameState, permanent_id: str) -> GameState:
    """Detect Saddle on the entering permanent at ETB (BLI 2025).

    For a human player this queues ``pending_saddle_choice`` with the list of valid
    target creatures and returns WITHOUT attaching — the permanent stays loose on
    the battlefield until resolved via the API choice handler (mirrors Equip's
    deferred-attach pattern). For an AI player it auto-resolves by attaching to the
    highest-power eligible creature it controls via ``_apply_equip``.

    No eligible creature => pure no-op returning the SAME object (Q4); non-saddled
    permanents are likewise a strict no-op so they stay byte-identical.
    """
    perm = next((p for p in game_state.battlefield if p.id == permanent_id), None)
    if perm is None:
        logger.debug("Saddle: permanent %s not on battlefield, returning unchanged state", permanent_id)
        return game_state

    card = perm.card
    oracle_text = card.oracle_text or ""

    # Guard (Q1): only process cards that actually carry Saddle. Anything else is a
    # strict no-op returning the SAME object so non-saddled permanents stay identical.
    if not SaddleKeyword.from_oracle_text(oracle_text):
        logger.debug("Saddle: %s has no Saddle keyword, returning unchanged state", card.name)
        return game_state

    # CR 702.XX (Equip parity): an already-attached saddle can't be re-saddled to a
    # (possibly different) creature. Re-invoking apply on a permanent that is already
    # attached would otherwise reattach it and leave a stale id in the old host's
    # attachments list — so this is a strict no-op returning the SAME object (Q4).
    if perm.attached_to is not None:
        logger.debug(
            "Saddle: %s already attached (%s), cannot attach again",
            card.name, perm.attached_to,
        )
        return game_state

    controller = perm.controller
    is_human = bool(
        getattr(game_state, "human_player_name", None) is not None
        and controller == game_state.human_player_name
    )

    # Human path: queue the choice; do NOT attach yet. The human later picks which
    # creature to saddle via the saddle_confirm handler (mirrors Equip/Crew).
    if is_human:
        eligible_ids = [p.id for p in _eligible_creatures(game_state, controller)]
        new_state = game_state.model_copy(update={
            "pending_saddle_choice": {
                "player": controller,
                "card_id": card.id,
                "permanent_id": permanent_id,
                "card_name": card.name,
                "available_creatures": eligible_ids,
                "resolved": False,
            }
        })
        logger.info(
            "Saddle: queued choice for %s to saddle %s, %d creature(s) available",
            controller, card.name, len(eligible_ids),
        )
        return new_state

    # AI path: attach to the highest-power eligible creature. No eligible target =>
    # pure no-op returning the SAME object (Q4); the permanent enters loose. Ties are
    # broken deterministically by ascending permanent id so results are stable.
    creatures = _eligible_creatures(game_state, controller)
    if not creatures:
        logger.debug("Saddle: %s has no eligible creature to attach to at ETB", card.name)
        return game_state

    chosen = sorted(creatures, key=lambda c: (-_creature_power(c), c.id))[0]
    from mtg_engine.engine.stack import _apply_equip
    gs = _apply_equip(game_state, permanent_id, chosen.id)
    logger.info(
        "Saddle: AI attached %s to %s at ETB",
        card.name, chosen.card.name,
    )
    return gs


def resolve_saddle_choice(
    game_state: GameState,
    choice_id: str,
    target_perm_id: str | None,
) -> GameState:
    """Resolve a human Saddle attachment choice (BLI 2025).

    Attaches the pending saddle permanent to ``target_perm_id`` via the shared
    ``_apply_equip`` helper and clears ``pending_saddle_choice``. When
    ``target_perm_id`` is omitted or not among the eligible creatures the choice is
    simply cleared without attaching (graceful decline). Returns a new GameState on
    success or the SAME object when there is no matching pending choice / action
    (Q4).
    """
    pending = getattr(game_state, "pending_saddle_choice", None)
    if not pending or choice_id != "saddle_confirm":
        return game_state

    saddle_perm_id = pending.get("permanent_id")
    available = set(pending.get("available_creatures", []))

    # Decline / invalid target: just clear the pending choice (no attach).
    if not target_perm_id or target_perm_id not in available:
        logger.debug(
            "Saddle: %s declined/invalid attachment (target=%r), clearing pending",
            pending.get("player"), target_perm_id,
        )
        return game_state.model_copy(update={"pending_saddle_choice": None})

    from mtg_engine.engine.stack import _apply_equip
    gs = _apply_equip(game_state, saddle_perm_id, target_perm_id)
    logger.info(
        "Saddle: %s attached %s to %s",
        pending.get("player"),
        next((p.card.name for p in game_state.battlefield if p.id == saddle_perm_id), "?"),
        target_perm_id,
    )
    return gs.model_copy(update={"pending_saddle_choice": None})
