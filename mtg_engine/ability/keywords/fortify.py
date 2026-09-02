"""Fortify keyword (CR 702.54a, current CR 702.67a).

Fortify is an activated ability of Fortification cards (CR 301.7):

    "Fortify [cost]" means "[cost]: Attach this Fortification to target land
    you control. Activate this ability only any time you could cast a sorcery."

A Fortification is an artifact with the land subtype Fortification — it is a
**land** that can be played as a land drop and, once on the battlefield, can
be attached to another land you control (the land-analogue of Equip).

Only two cards in all of MTG use Fortify: Darksteel Garrison and C.A.M.P.

Pure transforms throughout (``model_copy``); lazy imports to avoid circular
dependencies (mirror ``dash.py``).
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword
from mtg_engine.models.game import Card, Step

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, ManaPool, Permanent

logger = logging.getLogger(__name__)

# "Fortify {3}" / "Fortify {2}{R}" / "Fortify—{1}{G}" — the cost is a run of
# one or more {…} symbols immediately following the keyword.
# NB: the opening brace must be inside the repeated non-capturing group,
# otherwise only the first {X} chunk is matched.
_FORTIFY_PATTERN = re.compile(
    r"\bfortify\s*[—\-]?\s*((?:\{[^{}]*\}\s*)+)",
    re.IGNORECASE,
)


def _strip_tap(cost: str) -> str:
    """Remove a {T} component from an activation cost (mana part only).

    Fortify costs do not include tap per CR 702.54a, but a hypothetical
    "{T}{3}" cost is accepted here — the ``/activate`` endpoint machinery
    handles the tap. Returns the mana-only remainder ("" when empty).
    """
    return re.sub(r"\{T\}", "", cost).strip().strip(",").strip()


def _compute_payment(pool: "ManaPool", cost: str) -> dict[str, int]:
    """Build a greedy payment dict for a mana cost.

    Colored symbols are paid with the matching color; a {C} requirement is
    paid from the colorless pool; generic is paid from whatever remains
    (colorless first, then any color). The caller must gate with
    ``can_pay_cost()`` first, so the payment is guaranteed valid for
    ``pay_cost()``.
    """
    from mtg_engine.engine.mana import parse_mana_cost

    cost_dict = parse_mana_cost(cost)
    payment: dict[str, int] = {}

    # Colored mana: pay with the matching color.
    for color in ("W", "U", "B", "R", "G"):
        needed = cost_dict.get(color, 0)
        if needed:
            payment[color] = payment.get(color, 0) + needed

    # Colorless-specific requirement ({C}).
    needed_c = cost_dict.get("C", 0)
    if needed_c:
        payment["C"] = payment.get("C", 0) + needed_c

    # Generic mana: pay from the remaining pool, colorless first.
    remaining = cost_dict.get("generic", 0)
    for color in ("C", "W", "U", "B", "R", "G"):
        if remaining <= 0:
            break
        available = getattr(pool, color, 0) - payment.get(color, 0)
        take = min(remaining, available)
        if take > 0:
            payment[color] = payment.get(color, 0) + take
            remaining -= take

    return payment


class Fortify(CostKeyword):
    """Fortify keyword (CR 702.54a) — attach this Fortification to a land."""

    name = "fortify"

    # ── Detection / parsing ──────────────────────────────────────────────
    @staticmethod
    def parse_fortify_cost(oracle_text: str) -> str | None:
        """Parse the cost from a "Fortify {cost}" clause.

        "Fortify {3}" → "{3}"; "Fortify {2}{R}" → "{2}{R}"; else None.
        """
        match = _FORTIFY_PATTERN.search(oracle_text or "")
        return match.group(1).strip() if match else None

    @staticmethod
    def has_fortify(card: Card) -> bool:
        """True if "fortify" is in card.keywords or a "Fortify {cost}" clause exists."""
        if any("fortify" in (k or "").lower() for k in (card.keywords or [])):
            return True
        return Fortify.parse_fortify_cost(card.oracle_text or "") is not None

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """True if a "Fortify {cost}" clause is present (Flashback/Escape/Dash convention)."""
        return Fortify.parse_fortify_cost(oracle_text) is not None

    @staticmethod
    def is_fortification(card: Card) -> bool:
        """True if the type line has the Fortification subtype (CR 301.7 — it's a land)."""
        return "fortification" in (card.type_line or "").lower()

    @staticmethod
    def is_land_card(card: Card) -> bool:
        """True if the card is a land: "land" in type line, or a Fortification.

        Used for land-drop validation and Fortify target validation.
        """
        tl = (card.type_line or "").lower()
        return "land" in tl or Fortify.is_fortification(card)

    # ── Application ──────────────────────────────────────────────────────
    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target_land_id: str | None = None,
    ) -> "GameState":
        """Apply the full Fortify logic (CR 702.54a). Pure transform.

        - Validates the Fortification is on the battlefield and controlled by
          the acting player (``priority_holder``).
        - Enforces sorcery speed (acting player's main phase, empty stack).
        - Validates the target is a land-like permanent the acting player
          controls (not the source itself; a Fortification is a legal target
          since it is a land).
        - Pays the Fortify cost (mana only).
        - Delegates the attach to ``engine.stack._apply_fortify`` (which fires
          ``check_attach_triggers``).

        Returns a new ``GameState`` on success; returns the **same object**
        (no-op) when any validation fails or the cost is unaffordable.
        """
        from mtg_engine.engine.mana import can_pay_cost, pay_cost
        from mtg_engine.engine.zones import get_player

        card = permanent.card
        oracle = card.oracle_text or ""

        # Guard: only process cards that actually have the Fortify keyword.
        if not self.has_fortify(card):
            logger.debug("%s: %s does not have Fortify keyword, no-op", permanent.controller, card.name)
            return game_state

        cost = self.parse_fortify_cost(oracle)
        if not cost:
            logger.debug("%s: %s has no parseable Fortify cost, no-op", permanent.controller, card.name)
            return game_state

        acting_player = game_state.priority_holder

        # Source must be on the battlefield and controlled by the acting player.
        source_on_battlefield = any(p.id == permanent.id for p in game_state.battlefield)
        if not source_on_battlefield or permanent.controller != acting_player:
            logger.debug("%s: Fortify source %s not on battlefield/controlled by %s, no-op",
                         acting_player, card.name, permanent.controller)
            return game_state

        # Sorcery speed (CR 702.54a): acting player's main phase, empty stack.
        if not (
            game_state.active_player == acting_player
            and game_state.step == Step.MAIN
            and not game_state.stack
        ):
            logger.debug("%s: Fortify on %s rejected — not sorcery speed", acting_player, card.name)
            return game_state

        # Target validation: a land-like permanent the acting player controls
        # (a Fortification is a land, so it is a legal target) — not itself.
        if not target_land_id:
            logger.debug("%s: Fortify on %s has no target land, no-op", acting_player, card.name)
            return game_state
        target_perm = next((p for p in game_state.battlefield if p.id == target_land_id), None)
        if target_perm is None:
            logger.debug("%s: Fortify target %s not on battlefield, no-op", acting_player, target_land_id)
            return game_state
        if target_perm.controller != acting_player:
            logger.debug("%s: Fortify target %s not controlled by %s, no-op",
                         acting_player, target_perm.card.name, acting_player)
            return game_state
        if not self.is_land_card(target_perm.card):
            logger.debug("%s: Fortify target %s is not a land, no-op", acting_player, target_perm.card.name)
            return game_state
        if target_perm.id == permanent.id:
            logger.debug("%s: Fortify target is the source %s, no-op", acting_player, card.name)
            return game_state

        # Pay the Fortify cost (mana only; {T} is handled by /activate machinery).
        player = get_player(game_state, acting_player)
        if player is None:
            logger.warning("Player not found for Fortify resolution: %s", acting_player)
            return game_state
        mana_part = _strip_tap(cost)
        gs = game_state
        if mana_part:
            if not can_pay_cost(player.mana_pool, mana_part):
                logger.debug("%s: Fortify cost %s unaffordable, no-op", acting_player, cost)
                return game_state
            try:
                payment = _compute_payment(player.mana_pool, mana_part)
                new_pool = pay_cost(player.mana_pool, mana_part, payment)
            except ValueError:
                logger.debug("%s: Fortify payment for %s invalid, no-op", acting_player, cost)
                return game_state
            new_players = [
                p.model_copy(update={"mana_pool": new_pool}) if p.name == acting_player else p
                for p in gs.players
            ]
            gs = gs.model_copy(update={"players": new_players})

        # Delegate the attach (fires check_attach_triggers).
        from mtg_engine.engine.stack import _apply_fortify
        gs = _apply_fortify(gs, permanent.id, target_perm.id)
        logger.info("%s: Fortify attached %s to %s (cost %s)",
                    acting_player, card.name, target_perm.card.name, cost)
        return gs


# ── Module-level convenience functions (Sprint-7 wiring convention) ────────

def apply_fortify(
    game_state: "GameState",
    permanent: "Permanent",
    target_land_id: str | None = None,
) -> "GameState":
    """Convenience wrapper: ``Fortify().apply(game_state, permanent, target_land_id)``."""
    return Fortify().apply(game_state, permanent, target_land_id)


def resolve_fortify_with_ai(game_state: "GameState", permanent_id: str) -> "GameState":
    """AI auto-attach: attach to the first valid land the AI controls if affordable.

    Deterministic selection: the first land-like permanent (in battlefield
    order) controlled by the Fortification's controller, excluding the source.

    No-op (returns the **same object**) when the permanent is missing or not a
    Fortify card, timing is not sorcery speed for the controller, no valid
    land target exists, or the cost is unaffordable.
    """
    from mtg_engine.engine.mana import can_pay_cost, pay_cost
    from mtg_engine.engine.zones import get_player

    perm = next((p for p in game_state.battlefield if p.id == permanent_id), None)
    if perm is None:
        logger.debug("resolve_fortify_with_ai: permanent %s not on battlefield, no-op", permanent_id)
        return game_state
    card = perm.card
    if not Fortify.has_fortify(card):
        logger.debug("resolve_fortify_with_ai: %s does not have Fortify keyword, no-op", card.name)
        return game_state
    cost = Fortify.parse_fortify_cost(card.oracle_text or "")
    if not cost:
        logger.debug("resolve_fortify_with_ai: %s has no parseable Fortify cost, no-op", card.name)
        return game_state
    controller = perm.controller

    # Sorcery speed for the controller: their main phase, empty stack.
    if not (
        game_state.active_player == controller
        and game_state.step == Step.MAIN
        and not game_state.stack
    ):
        logger.debug("resolve_fortify_with_ai: %s rejected — not sorcery speed", card.name)
        return game_state

    # Deterministic target: first land-like permanent the AI controls (not self).
    target_id = next(
        (
            p.id for p in game_state.battlefield
            if p.controller == controller
            and p.id != perm.id
            and Fortify.is_land_card(p.card)
        ),
        None,
    )
    if target_id is None:
        logger.debug("resolve_fortify_with_ai: %s has no valid land target, no-op", card.name)
        return game_state

    player = get_player(game_state, controller)
    if player is None:
        logger.warning("Player not found for Fortify AI resolution: %s", controller)
        return game_state
    mana_part = _strip_tap(cost)
    if mana_part and not can_pay_cost(player.mana_pool, mana_part):
        logger.debug("resolve_fortify_with_ai: %s cost %s unaffordable, no-op", card.name, cost)
        return game_state

    gs = game_state
    if mana_part:
        try:
            payment = _compute_payment(player.mana_pool, mana_part)
            new_pool = pay_cost(player.mana_pool, mana_part, payment)
        except ValueError:
            logger.debug("resolve_fortify_with_ai: %s payment invalid, no-op", card.name)
            return game_state
        new_players = [
            p.model_copy(update={"mana_pool": new_pool}) if p.name == controller else p
            for p in gs.players
        ]
        gs = gs.model_copy(update={"players": new_players})

    from mtg_engine.engine.stack import _apply_fortify
    gs = _apply_fortify(gs, perm.id, target_id)
    logger.info("resolve_fortify_with_ai: %s (AI %s) attached to %s",
                card.name, controller, target_id)
    return gs
