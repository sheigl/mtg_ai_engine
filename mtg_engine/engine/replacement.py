"""
Replacement effects. REQ-R04, REQ-R05, REQ-R06.
CR 614: "instead" effects intercept events before they happen.
CR 616: multiple replacement effects — controller chooses order.
"""
import logging
from typing import Any
from pydantic import BaseModel
from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)


class GameEvent(BaseModel):
    """A game event that may be intercepted by replacement effects."""
    event_type: str   # "damage", "destroy", "draw", "zone_change", "discard", etc.
    source_id: str | None = None
    target_id: str | None = None
    amount: int = 0
    from_zone: str | None = None
    to_zone: str | None = None
    replaced: bool = False
    modified_amount: int | None = None
    redirect_target_id: str | None = None
    cancelled: bool = False
    extra: dict = {}


class ReplacementEffect(BaseModel):
    """A replacement effect that can modify a GameEvent."""
    effect_id: str
    source_permanent_id: str
    controller: str
    description: str
    event_types: list[str]     # which event types this applies to
    is_self_replacement: bool = False  # CR 616.1a

    class Config:
        arbitrary_types_allowed = True


def _get_replacement_effects(game_state: GameState) -> list[ReplacementEffect]:
    """
    Collect all active replacement effects from permanents.
    Currently handles: shield counters, regeneration shields,
    damage prevention (simplified).
    """
    effects: list[ReplacementEffect] = []

    for perm in game_state.battlefield:
        oracle = (perm.card.oracle_text or "").lower()

        # Shield counter: "if ~ would be destroyed, remove a shield counter instead"
        if perm.counters.get("shield", 0) > 0:
            effects.append(ReplacementEffect(
                effect_id=f"shield_{perm.id}",
                source_permanent_id=perm.id,
                controller=perm.controller,
                description=f"{perm.card.name}: shield counter prevents destruction",
                event_types=["destroy"],
                is_self_replacement=True,
            ))

        # Regeneration shield (if flagged via counter)
        if perm.counters.get("__regen_shield__", 0) > 0:
            effects.append(ReplacementEffect(
                effect_id=f"regen_{perm.id}",
                source_permanent_id=perm.id,
                controller=perm.controller,
                description=f"{perm.card.name}: regeneration shield",
                event_types=["destroy"],
                is_self_replacement=True,
            ))

    return effects


def get_applicable_replacements(
    event: GameEvent, game_state: GameState
) -> list[ReplacementEffect]:
    """
    Return all replacement effects that apply to the given event. REQ-R04.
    CR 614.4: Effects must exist before the event occurs.
    """
    all_effects = _get_replacement_effects(game_state)
    applicable: list[ReplacementEffect] = []

    for effect in all_effects:
        if event.event_type not in effect.event_types:
            continue
        # For target-specific effects, check the target
        if event.target_id and event.target_id != effect.source_permanent_id:
            # Self-replacement: only applies to the permanent itself
            if effect.is_self_replacement:
                continue
        applicable.append(effect)

    # CR 616.1a: Self-replacement effects must be chosen first
    applicable.sort(key=lambda e: (0 if e.is_self_replacement else 1))
    return applicable


def apply_replacement(
    event: GameEvent, effect: ReplacementEffect, game_state: GameState
) -> tuple[GameEvent, GameState]:
    """
    Apply one replacement effect to an event. CR 614.6.
    Returns the (possibly modified) event and updated game state.
    """
    target_perm = next(
        (p for p in game_state.battlefield if p.id == event.target_id), None
    )

    if effect.effect_id.startswith("shield_") and target_perm:
        # Remove shield counter instead of being destroyed (CR 614.1a)
        target_perm.counters["shield"] = max(0, target_perm.counters.get("shield", 0) - 1)
        if target_perm.counters["shield"] == 0:
            del target_perm.counters["shield"]
        event.cancelled = True
        logger.info("Shield counter removed on %s, destruction cancelled", target_perm.card.name)

    elif effect.effect_id.startswith("regen_") and target_perm:
        # Regeneration: remove damage, tap, remove from combat
        target_perm.counters.pop("__regen_shield__", None)
        target_perm.damage_marked = 0
        target_perm.tapped = True
        event.cancelled = True
        logger.info("Regeneration used on %s", target_perm.card.name)

    return event, game_state


def process_event(
    event: GameEvent,
    game_state: GameState,
    choice_fn: Any = None,  # called when player must choose replacement order
) -> tuple[GameEvent, GameState]:
    """
    Process an event through all applicable replacement effects. REQ-R04, REQ-R05.
    CR 616.1f: apply one, then repeat until no more applicable.

    choice_fn(player, options) → chosen_index, for REQ-R05 multi-replacement ordering.
    Defaults to choosing first available (deterministic for engine use).
    """
    applied: set[str] = set()

    for _ in range(20):  # safety limit
        applicable = [
            e for e in get_applicable_replacements(event, game_state)
            if e.effect_id not in applied
        ]
        if not applicable:
            break

        # CR 616.1: controller of affected object chooses
        # For now, always pick the first (self-replacement first due to sorting)
        chosen = applicable[0]
        applied.add(chosen.effect_id)
        event, game_state = apply_replacement(event, chosen, game_state)

        if event.cancelled:
            break

    return event, game_state


def apply_damage_event(
    game_state: GameState,
    source_card_name: str,
    source_keywords: list[str],
    target_id: str,
    damage: int,
    is_combat: bool = False,
) -> GameState:
    """
    Apply damage through the replacement effect system. REQ-R07, REQ-R08.
    Handles: deathtouch, lifelink, infect (REQ-R12).
    """
    if damage <= 0:
        return game_state

    event = GameEvent(
        event_type="damage",
        source_id=source_card_name,
        target_id=target_id,
        amount=damage,
    )
    event, game_state = process_event(event, game_state)
    if event.cancelled:
        return game_state

    final_damage = event.modified_amount if event.modified_amount is not None else event.amount
    redirect = event.redirect_target_id or target_id

    has_deathtouch = "deathtouch" in source_keywords
    has_lifelink   = "lifelink" in source_keywords
    has_infect     = "infect" in source_keywords

    from mtg_engine.engine.zones import get_player

    # Apply damage to target
    target_perm = next((p for p in game_state.battlefield if p.id == redirect), None)
    if target_perm:
        if has_infect:
            # REQ-R12: infect damage to creatures as -1/-1 counters
            target_perm.counters["-1/-1"] = target_perm.counters.get("-1/-1", 0) + final_damage
        else:
            target_perm.damage_marked += final_damage
        if has_deathtouch and final_damage > 0:
            # REQ-R10: mark for deathtouch SBA (CR 702.2b)
            target_perm.counters["__deathtouch_damage__"] = (
                target_perm.counters.get("__deathtouch_damage__", 0) + final_damage
            )
    else:
        # Target is a player
        for player in game_state.players:
            if player.name == redirect:
                if has_infect:
                    # REQ-R12: infect damage to players as poison counters
                    player.poison_counters += final_damage
                else:
                    player.life -= final_damage
                break

    # Lifelink: controller of the SOURCE gains life (REQ-R11)
    # (simplified: lifelink handled in combat.py where we know the attacker's controller)

    return game_state
