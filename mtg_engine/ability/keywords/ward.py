"""Ward keyword (CR 702.145).

Ward is a triggered ability that counters a spell or ability unless its
controller pays an additional cost. Ward {2} means "Whenever this
permanent becomes the target of a spell or ability, counter it unless
that spell or ability's controller pays {2}." (CR 702.145a)

This module implements :meth:`Ward.apply` as a pure transform that resolves ONE
ward trigger: given the ward permanent and the opponent targeting it, return the
new ``GameState`` after either queueing a pay/counter choice for a human caster or
auto-resolving for an AI caster (pay if affordable, otherwise counter the spell).

* Meaningful changes return a **new** ``GameState`` built with
  ``model_copy(update=...)`` — never mutate live players in place.
* Every no-op path returns the **same** ``game_state`` object so callers can
  assert ``is gs`` and repeated events cannot double-fire (Q1/Q4).

Human vs AI:

* A human caster (``game_state.human_player_name`` matches the targeting caster)
  queues ``pending_ward_payment`` with the ward cost and the targeting spell id,
  returning **without** resolving. The choice is resolved later via the
  ``ward_pay`` / ``ward_counter`` handlers in the API router.
* An AI caster auto-resolves by affordability: pays the ward cost if the mana pool
  can cover it (the spell continues), otherwise counters the targeting spell
  (CR 702.157b).

Ward is fired from stack.py's cast_spell becomes-target flow; see
:func:`apply_ward`. Self-targeting never triggers Ward (CR 702.145b): a permanent
that is its own target does not counter the spell.

Activated abilities resolve inline (no StackObject), so the ability-oriented
resolver :func:`apply_ward_to_ability` returns an *outcome string* instead of
manipulating the stack: ``"proceed"`` (no ward / AI paid / self-targeting no-op —
apply the effect), ``"countered"`` (AI could not pay — do NOT apply the effect),
or ``"deferred"`` (human targeter — ``pending_ward_payment`` is queued with
``targeting_type="ability"`` and the effect is deferred to the ``ward_pay`` /
``ward_counter`` choice handlers in the API router).
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import TriggeredKeyword

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent, PlayerState, StackObject

logger = logging.getLogger(__name__)

# "Ward {3}" / "Ward—Pay {2}{R}" — the cost is required for detection/parsing.
_WARD_PATTERN = re.compile(
    r"ward\s*[—\-]?\s*(?:pay\s+)?(\{(?:[^}]+}\s*)+)", re.IGNORECASE
)
# "Ward 2" — a bare numeric ward (no braces) still parses to that cost.
_WARD_COST_PATTERN = re.compile(r"ward\s+(\d+)", re.IGNORECASE)


class Ward(TriggeredKeyword):
    name = "ward"

    def __init__(self, cost: str = "{2}"):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("ward" in k.lower() for k in keywords)
            or bool(_WARD_PATTERN.search(oracle))
            or bool(_WARD_COST_PATTERN.search(oracle))
        )

    @staticmethod
    def has_ward(keywords: list[str]) -> bool:
        """True if the keyword list contains a Ward instance."""
        return any("ward" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return (
            bool(_WARD_PATTERN.search(oracle_text))
            or bool(_WARD_COST_PATTERN.search(oracle_text))
        )

    @staticmethod
    def parse_ward_cost(oracle_text: str) -> str:
        match = _WARD_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        match = _WARD_COST_PATTERN.search(oracle_text or "")
        if match:
            n = int(match.group(1))
            return "{" + str(n) + "}"
        return "{2}"

    @classmethod
    def from_oracle(cls, oracle_text: str) -> "Ward | None":
        if cls.from_oracle_text(oracle_text):
            cost = cls.parse_ward_cost(oracle_text)
            return cls(cost=cost)
        return None

    def apply(
        self,
        game_state: GameState,
        permanent: Permanent,
        target: "StackObject | None" = None,
        *,
        caster_name: str | None = None,
    ) -> GameState:
        """Resolve one Ward trigger (CR 702.145b).

        ``permanent`` is the ward creature owned by its controller; ``caster_name``
        is the opponent targeting it. When ``caster_name`` is omitted there is no
        identifiable targeter, so this is a strict no-op returning the **same**
        object (Q4).

        Guards:

        *         No caster → no-op (same object).
        * Self-targeting (``caster_name == ward controller``) → no trigger at all
          (CR 702.145b): return the **same** object.

        Otherwise resolve via :meth:`_resolve` — queue for a human caster, or
        auto-resolve by affordability for an AI caster.
        """
        # No identifiable targeter → strict no-op (same object). Guards against a
        # spurious ``pending_ward_payment={"player": None}`` when the caller omits
        # the caster and ``human_player_name`` is also unset.
        if not caster_name:
            logger.debug(
                "Ward: %s has no caster; returning unchanged state",
                permanent.card.name,
            )
            return game_state

        ward_controller = getattr(permanent, "controller", None)
        if not ward_controller:
            logger.debug(
                "Ward: %s has no controller; returning unchanged state",
                permanent.card.name,
            )
            return game_state

        # CR 702.145b: Ward only triggers against opponents targeting your own
        # permanent — never when you target it yourself.
        if caster_name and caster_name == ward_controller:
            logger.debug(
                "Ward: %s targeted by its own controller; no trigger (CR 702.145b)",
                permanent.card.name,
            )
            return game_state

        ward_cost = self.cost or Ward.parse_ward_cost(permanent.card.oracle_text or "")
        if not ward_cost:
            logger.debug(
                "Ward: %s has no parseable ward cost; returning unchanged state",
                permanent.card.name,
            )
            return game_state

        targeting_spell_id = getattr(target, "id", None) if target is not None else ""

        # Human caster → queue the pay/counter choice for priority resolution.
        if getattr(game_state, "human_player_name", None) == caster_name:
            new_pending = {
                "player": caster_name,
                "ward_cost": ward_cost,
                "targeting_spell_id": targeting_spell_id or "",
                "target_permanent_id": permanent.id,
            }
            logger.info(
                "Ward queued for %s: pay %s or spell is countered",
                caster_name, ward_cost,
            )
            return game_state.model_copy(update={"pending_ward_payment": new_pending})

        # AI caster → auto-resolve by affordability.
        return self._resolve_ai(game_state, permanent, ward_cost, caster_name, targeting_spell_id)

    def _resolve_ai(
        self,
        game_state: GameState,
        permanent: Permanent,
        ward_cost: str,
        caster_name: str,
        targeting_spell_id: str,
    ) -> GameState:
        """Auto-resolve a Ward trigger for an AI caster (CR 702.145b / 702.157b).

        Pays the ward cost from the caster's mana pool if affordable (the spell
        continues), otherwise counters the targeting spell by removing it from the
        stack and moving its source card to its controller's graveyard. Pure
        transform: returns a new GameState with ``pending_ward_payment`` cleared.
        """
        from mtg_engine.engine.mana import can_pay_cost, pay_cost as _pay_cost

        player = _get_player(game_state, caster_name)
        if player is None:
            return game_state.model_copy(update={"pending_ward_payment": None})

        if ward_cost and can_pay_cost(player.mana_pool, ward_cost):
            cost_dict = _parse_mana_cost(ward_cost)
            payment = _compute_payment(player.mana_pool, cost_dict)
            if payment:
                new_pool = _pay_cost(player.mana_pool, ward_cost, payment)
                updated_player = player.model_copy(update={"mana_pool": new_pool})
                new_players = [
                    updated_player if p.name == caster_name else p
                    for p in game_state.players
                ]
                logger.info(
                    "Ward: %s paid %s to avoid counter; spell continues",
                    caster_name, ward_cost,
                )
                return game_state.model_copy(
                    update={"players": new_players, "pending_ward_payment": None}
                )

        # Cannot / will not pay → counter the targeting spell (CR 702.157b).
        if targeting_spell_id and game_state.stack:
            countered = next(
                (s for s in game_state.stack if s.id == targeting_spell_id), None
            )
            if countered is not None:
                new_stack = [s for s in game_state.stack if s.id != targeting_spell_id]
                owner = _get_player(game_state, countered.controller)
                logger.info(
                    "Ward: %s's spell %s countered for non-payment",
                    caster_name, countered.source_card.name,
                )
                if not countered.is_copy and owner is not None:
                    # Pure transform: build the graveyard change via model_copy
                    # and rebuild the players list (model_copy on GameState is
                    # SHALLOW — the players list and player objects are shared
                    # with the original state, so appending to
                    # ``owner.graveyard`` would corrupt the original state).
                    new_owner = owner.model_copy(
                        update={"graveyard": owner.graveyard + [countered.source_card]}
                    )
                    new_players = [
                        new_owner if p.name == owner.name else p
                        for p in game_state.players
                    ]
                    return game_state.model_copy(
                        update={
                            "stack": new_stack,
                            "players": new_players,
                            "pending_ward_payment": None,
                        }
                    )
                return game_state.model_copy(
                    update={"stack": new_stack, "pending_ward_payment": None}
                )

        # Nothing to counter (spell already gone) — just clear the pending choice.
        logger.debug(
            "Ward: clearing pending payment for %s; nothing left to resolve",
            caster_name,
        )
        return game_state.model_copy(update={"pending_ward_payment": None})


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _get_player(game_state: GameState, name: str) -> "PlayerState | None":
    """Return the player with ``name`` or ``None`` (does not raise)."""
    for p in game_state.players:
        if p.name == name:
            return p
    return None


def _compute_payment(pool, cost_dict: dict[str, int]) -> dict[str, int]:
    """Build a valid payment dict covering ``cost_dict`` from ``pool``.

    Satisfies explicit colored/colorless requirements first, then covers any
    generic remaining with leftover mana in canonical order (W,U,B,R,G,C). Returns
    an empty dict when the pool cannot cover the cost (caller treats that as
    unpayable).
    """
    avail = {
        "W": pool.W, "U": pool.U, "B": pool.B,
        "R": pool.R, "G": pool.G, "C": pool.C,
    }
    payment: dict[str, int] = {}

    # 1. Explicit colored requirements.
    for color in ("W", "U", "B", "R", "G"):
        need = cost_dict.get(color, 0)
        take = min(avail[color], need)
        if take > 0:
            payment[color] = take
            avail[color] -= take

    # 2. Colorless-specific requirement.
    need_c = cost_dict.get("C", 0)
    take_c = min(avail["C"], need_c)
    if take_c > 0:
        payment["C"] = take_c
        avail["C"] -= take_c

    # 3. Generic leftover — spend remaining mana in canonical order.
    generic_needed = cost_dict.get("generic", 0)
    for color in ("W", "U", "B", "R", "G", "C"):
        if generic_needed <= 0:
            break
        take = min(avail[color], generic_needed)
        if take > 0:
            payment[color] = payment.get(color, 0) + take
            avail[color] -= take
            generic_needed -= take

    return payment


def _parse_mana_cost(mana_cost: str) -> dict[str, int]:
    from mtg_engine.engine.mana import parse_mana_cost as _parse
    return _parse(mana_cost or "")


def apply_ward(
    game_state: GameState,
    permanent: Permanent,
    target: "StackObject | None" = None,
    *,
    caster_name: str | None = None,
) -> GameState:
    """Module-level convenience wrapper: ``Ward().apply(game_state, permanent)``.

    Primarily used by stack.py's becomes-target flow to fire Ward when an opponent
    targets a permanent that has the keyword. See :meth:`Ward.apply`.
    """
    return Ward().apply(game_state, permanent, target=target, caster_name=caster_name)


def apply_ward_to_ability(
    game_state: GameState,
    ward_perm: Permanent,
    *,
    caster_name: str | None = None,
) -> tuple[GameState, str]:
    """Resolve one Ward trigger for an ACTIVITY (CR 702.145a) — an activated
    ability that targets the ward permanent and resolves INLINE (no StackObject).

    ``ward_perm`` is the ward permanent; ``caster_name`` is the opponent
    activating the ability that targets it. Returns ``(new_game_state, outcome)``:

    * ``"proceed"`` — no ward fires, or an AI targeter paid the ward cost; the
      ability effect should apply. The no-op guards (no caster, no controller,
      self-targeting per CR 702.145b) return the **same** ``game_state`` object
      with this outcome (Q4).
    * ``"countered"`` — the AI targeter could not pay; the ability effect must
      NOT apply. There is no spell on the stack to remove, so no ``stack``
      manipulation happens here — the caller simply skips the effect (the
      activation cost was already paid by the caller and is consumed regardless).
    * ``"deferred"`` — the targeter is the human player; ``pending_ward_payment``
      is queued (tagged ``targeting_type="ability"``,
      ``targeting_spell_id=""``) and the effect must be deferred until the
      ``ward_pay`` / ``ward_counter`` choice handlers resolve it.

    The ward cost is parsed from ``ward_perm``'s oracle text via
    :meth:`Ward.parse_ward_cost` (a bare "Ward" with no parseable cost falls back
    to the keyword default). Pure transform: meaningful changes return a new
    ``GameState`` built with ``model_copy(update=...)``; no-op paths return the
    same object. Does not alter the spell-oriented :func:`apply_ward` path.
    """
    # No identifiable targeter → strict no-op (same object); the effect proceeds.
    if not caster_name:
        logger.debug(
            "Ward (ability): %s has no caster; returning unchanged state",
            ward_perm.card.name,
        )
        return game_state, "proceed"

    ward_controller = getattr(ward_perm, "controller", None)
    if not ward_controller:
        logger.debug(
            "Ward (ability): %s has no controller; returning unchanged state",
            ward_perm.card.name,
        )
        return game_state, "proceed"

    # CR 702.145b: Ward only triggers against opponents targeting your own
    # permanent — never when you target it yourself.
    if caster_name == ward_controller:
        logger.debug(
            "Ward (ability): %s targeted by its own controller; no trigger (CR 702.145b)",
            ward_perm.card.name,
        )
        return game_state, "proceed"

    ward_cost = Ward.parse_ward_cost(ward_perm.card.oracle_text or "")
    if not ward_cost:
        logger.debug(
            "Ward (ability): %s has no parseable ward cost; returning unchanged state",
            ward_perm.card.name,
        )
        return game_state, "proceed"

    # Human targeter → queue the pay/counter choice (ability-tagged) for
    # resolution via the ward_pay / ward_counter API handlers.
    if getattr(game_state, "human_player_name", None) == caster_name:
        new_pending = {
            "player": caster_name,
            "ward_cost": ward_cost,
            "targeting_spell_id": "",  # inline ability — no StackObject id
            "target_permanent_id": ward_perm.id,
            "targeting_type": "ability",
        }
        logger.info(
            "Ward (ability) queued for %s: pay %s or the ability is countered",
            caster_name, ward_cost,
        )
        return (
            game_state.model_copy(update={"pending_ward_payment": new_pending}),
            "deferred",
        )

    # AI targeter → auto-resolve by affordability (CR 702.145a).
    from mtg_engine.engine.mana import can_pay_cost, pay_cost as _pay_cost

    player = _get_player(game_state, caster_name)
    if player is None:
        # No payer to collect the ward cost from → the ability is countered.
        logger.info(
            "Ward (ability): %s has no player entry; ability countered",
            caster_name,
        )
        return game_state, "countered"

    if ward_cost and can_pay_cost(player.mana_pool, ward_cost):
        cost_dict = _parse_mana_cost(ward_cost)
        payment = _compute_payment(player.mana_pool, cost_dict)
        if payment:
            new_pool = _pay_cost(player.mana_pool, ward_cost, payment)
            updated_player = player.model_copy(update={"mana_pool": new_pool})
            new_players = [
                updated_player if p.name == caster_name else p
                for p in game_state.players
            ]
            logger.info(
                "Ward (ability): %s paid %s; ability continues",
                caster_name, ward_cost,
            )
            return (
                game_state.model_copy(
                    update={"players": new_players, "pending_ward_payment": None}
                ),
                "proceed",
            )

    # Cannot / will not pay → the ability is countered (CR 702.157b). No stack
    # object exists for an inline ability, so the state is returned unchanged
    # and the caller must skip the effect.
    logger.info(
        "Ward (ability): %s cannot pay %s; ability countered",
        caster_name, ward_cost,
    )
    return game_state, "countered"
