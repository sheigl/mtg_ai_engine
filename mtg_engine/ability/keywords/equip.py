"""Equip keyword (CR 702.5).

Equip {cost} means "Activate this ability only any time you could cast a
sorcery: Attach this Equipment to target creature you control. Play this
ability only any time you could cast a sorcery."
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)

_EQUIP_PATTERN = re.compile(
    r"equip\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE
)
_EQUIP_PLAIN = re.compile(r"\bequip\b", re.IGNORECASE)
# Static +N/+N bonus on the equipped creature: "Equipped creature gets +2/+2".
_EQUIP_BONUS_RE = re.compile(r"gets\s+([+-]?\d+)\s*/\s*([+-]?\d+)")
_EQUIP_BONUS_FALLBACK_RE = re.compile(r"\b([+-]?\d+)/([+-]?\d+)\b")


class Equip(CostKeyword):
    name = "equip"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("equip" in k.lower() for k in keywords)
            or bool(_EQUIP_PLAIN.search(oracle))
        )

    @staticmethod
    def has_equip(keywords: list[str]) -> bool:
        return any("equip" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_EQUIP_PLAIN.search(oracle_text))

    @staticmethod
    def parse_equip_cost(oracle_text: str) -> str | None:
        match = _EQUIP_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Equip | None:
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_equip_cost(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        """Activate an Equipment's equip ability (CR 702.5).

        Equip {cost} means "{cost}: Attach this Equipment to target creature you
        control. Activate this ability only any time you could cast a sorcery."

        Validation / timing gate (Q1):

        * The card must actually carry the Equip keyword, otherwise this is a
          strict no-op returning the **same** ``game_state`` object (so repeated
          events cannot double-fire).
        * The Equipment must be on the battlefield and controlled by the player
          who holds priority. Anything else is a strict no-op.
        * Sorcery-speed only (CR 702.5): it must be the controller's own main
          phase with an empty stack. Off-timing returns the **same** object.
        * The Equipment cannot already be attached to something (CR 702.6b); a
          pre-attached source is a strict no-op.

        Human vs AI:

        * A human player (``game_state.human_player_name`` matches the controller)
          queues ``pending_equip_choice`` with the list of eligible creatures and
          returns **without** attaching — the choice is resolved later via the
          ``equip_confirm`` handler in the API router.
        * An AI player auto-resolves by equipping to the highest-power eligible
          creature it controls, attaching (via the shared ``_apply_equip`` helper)
          and reflecting the Equipment's static +N/+N as ``power_bonus`` /
          ``toughness_bonus`` on the creature so combat P/T is correct. If no
          eligible target exists the call is a pure no-op returning the same object.

        State transforms are pure: meaningful changes return a new GameState built
        with ``model_copy(update={...})``; every no-op path returns the SAME object
        so callers can assert ``is gs`` (Q4).
        """
        card = permanent.card
        oracle_text = card.oracle_text or ""

        # Guard (Q1): only process cards that actually have Equip. Anything else
        # is a strict no-op returning the SAME object so repeated events cannot
        # double-fire.
        if not self.from_oracle_text(oracle_text):
            logger.debug("Equip: %s has no Equip keyword, returning unchanged state", card.name)
            return game_state

        controller = permanent.controller
        equip_perm_id = permanent.id

        # Validate: the Equipment must be on the battlefield and controlled by the
        # player holding priority. Anything else is a strict no-op.
        if controller is None or permanent.controller != game_state.priority_holder:
            logger.debug(
                "Equip: %s not controlled by priority holder (%s), returning unchanged state",
                card.name, game_state.priority_holder,
            )
            return game_state
        if not any(p.id == equip_perm_id for p in game_state.battlefield):
            logger.debug("Equip: %s not on battlefield, returning unchanged state", card.name)
            return game_state

        # Sorcery-speed timing (CR 702.5): controller's own main phase, empty stack.
        if not _sorcery_speed(game_state, controller):
            logger.debug("Equip: %s rejected — not sorcery speed for %s", card.name, controller)
            return game_state

        # CR 702.6b: an Equipment already attached can't be re-activated to attach
        # to a (possibly different) creature. A pre-attached source is a no-op.
        if permanent.attached_to is not None:
            logger.debug("Equip: %s already attached (%s), cannot activate", card.name, permanent.attached_to)
            return game_state

        # Human path: queue the choice; do NOT attach yet. The human later picks
        # which creature to equip via the equip_confirm handler (mirrors Crew).
        if getattr(game_state, "human_player_name", None) == controller:
            eligible_ids = [p.id for p in _eligible_creatures(game_state, controller)]
            new_state = game_state.model_copy(update={
                "pending_equip_choice": {
                    "player": controller,
                    "card_id": card.id,
                    "permanent_id": equip_perm_id,
                    "card_name": card.name,
                    "equipment_cost": self.cost or Equip.parse_equip_cost(oracle_text),
                    "available_creatures": eligible_ids,
                    "resolved": False,
                }
            })
            logger.info(
                "Equip: queued choice for %s to equip %s, %d creature(s) available",
                controller, card.name, len(eligible_ids),
            )
            return new_state

        # AI path: attach to the highest-power eligible creature. No eligible
        # target => pure no-op returning the SAME object (Q4). Ties are broken
        # deterministically by ascending permanent id so results are stable.
        creatures = _eligible_creatures(game_state, controller)
        if not creatures:
            logger.debug("Equip: %s has no eligible creature to equip", card.name)
            return game_state

        chosen = sorted(creatures, key=lambda c: (-_creature_power(c), c.id))[0]
        chosen_id = chosen.id

        from mtg_engine.engine.stack import _apply_equip
        gs = _apply_equip(game_state, equip_perm_id, chosen_id)

        # Reflect the Equipment's static +N/+N as P/T bonuses on the creature so
        # combat P/T is correct (layer 7b). Pure transform.
        gs = _apply_equip_bonus(gs, permanent, chosen_id)
        logger.info(
            "Equip: %s AI equipped to %s (%s +%d/%d)",
            controller, card.name, chosen.card.name, *parse_equip_bonus(oracle_text),
        )
        return gs


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def parse_equip_bonus(oracle_text: str) -> tuple[int, int]:
    """Return the static +N/+N (or +-N/+-N) bonus from an Equipment's oracle text.

    Matches the canonical "Equipped creature gets +2/+2" pattern first; falls back
    to a bare "+N/+N" token if no explicit "gets" clause is present. Returns
    ``(0, 0)`` when the card has no static P/T bonus (e.g. pure benefit Equipment).
    """
    text = oracle_text or ""
    match = _EQUIP_BONUS_RE.search(text)
    if not match:
        match = _EQUIP_BONUS_FALLBACK_RE.search(text)
    if not match:
        return 0, 0
    try:
        return int(match.group(1)), int(match.group(2))
    except (ValueError, TypeError):
        return 0, 0


def sorcery_speed(game_state: GameState, controller: str) -> bool:
    """True if ``controller`` may activate a sorcery-speed ability now.

    CR 702.5 / 608: it must be the controller's own main phase with an empty
    stack (and they hold priority).
    """
    from mtg_engine.models.game import Step
    return (
        game_state.active_player == controller
        and game_state.step == Step.MAIN
        and not game_state.stack
    )


def _sorcery_speed(game_state: GameState, controller: str) -> bool:
    return sorcery_speed(game_state, controller)


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

    Tokens count. This is the set of legal equip targets (CR 702.6): any creature
    you control — a tapped or summoning-sick creature may still be equipped. The
    caller is responsible for excluding the source when it is already attached.
    """
    return [
        perm
        for perm in game_state.battlefield
        if perm.controller == controller and _is_creature_perm(perm)
    ]


def _apply_equip_bonus(game_state: GameState, equipment: Permanent, creature_id: str) -> GameState:
    """Reflect the Equipment's static +N/+N as P/T bonuses on ``creature_id``.

    The bonus persists while attached (real Equip behaviour): it is NOT tagged
    with an expiry so it survives until the Equipment detaches. Revert via
    :func:`clear_equip_bonus`. Pure transform returning the same object when the
    Equipment has no static bonus or the creature cannot be found.
    """
    if not creature_id:
        return game_state

    power, toughness = parse_equip_bonus(equipment.card.oracle_text or "")
    if power == 0 and toughness == 0:
        # No static bonus to apply — leave state untouched (same object).
        return game_state

    new_battlefield = []
    changed = False
    for perm in game_state.battlefield:
        if perm.id == creature_id:
            new_battlefield.append(perm.model_copy(update={
                "power_bonus": power,
                "toughness_bonus": toughness,
            }))
            changed = True
        else:
            new_battlefield.append(perm)

    if not changed:
        return game_state
    return game_state.model_copy(update={"battlefield": new_battlefield})


def clear_equip_bonus(permanent: Permanent) -> Permanent:
    """Revert the static +N/+N bonus applied by :func:`_apply_equip_bonus`.

    Returns a copy with ``power_bonus`` / ``toughness_bonus`` reset to 0. Used on
    unattach (Equipment or its host leaving the battlefield). Pure transform;
    callers should rebuild the battlefield list with the returned permanent.
    """
    if permanent.power_bonus == 0 and permanent.toughness_bonus == 0:
        return permanent
    return permanent.model_copy(update={
        "power_bonus": 0,
        "toughness_bonus": 0,
        "power_bonus_expires": None,
        "toughness_bonus_expires": None,
    })


def apply_equip(game_state: GameState, permanent: Permanent) -> GameState:
    """Module-level convenience wrapper: ``Equip().apply(game_state, permanent)``."""
    return Equip().apply(game_state, permanent)


def resolve_equip_choice(
    game_state: GameState,
    player_name: str,
    creature_id: str | None = None,
) -> GameState:
    """Resolve a human Equip choice (CR 702.5).

    Attaches the pending Equipment to ``creature_id`` and reflects its +N/+N bonus.
    When ``creature_id`` is omitted the choice is simply cleared (declined) without
    attaching. Returns a new GameState on success or the **same** object when there
    is no matching pending choice (Q4).
    """
    pending = getattr(game_state, "pending_equip_choice", None)
    if not pending or pending.get("player") != player_name:
        return game_state

    equip_perm_id = pending.get("permanent_id")
    available = set(pending.get("available_creatures", []))

    # Decline / no target selected: just clear the pending choice.
    if not creature_id or creature_id not in available:
        logger.debug(
            "Equip: %s declined/invalid equip choice (target=%r), clearing pending",
            player_name, creature_id,
        )
        return game_state.model_copy(update={"pending_equip_choice": None})

    from mtg_engine.engine.stack import _apply_equip
    gs = _apply_equip(game_state, equip_perm_id, creature_id)

    equipment = next((p for p in game_state.battlefield if p.id == equip_perm_id), None)
    if equipment is not None:
        gs = _apply_equip_bonus(gs, equipment, creature_id)
        logger.info("Equip: %s equipped %s to %s", player_name, equipment.card.name, creature_id)

    return gs.model_copy(update={"pending_equip_choice": None})
