"""
Replacement effects. REQ-R04, REQ-R05, REQ-R06.
CR 614: "instead" effects intercept events before they happen.
CR 616: multiple replacement effects — controller chooses order.

Phase 800: REP-01 (prevention), REP-02 (draw replacement), REP-03 (duration).
"""
import logging
import uuid
from typing import Any
from pydantic import BaseModel, Field
from mtg_engine.models.game import GameState, DamagePreventionEffect

logger = logging.getLogger(__name__)


# ─── REP-02: Draw Replacement Effect Model ──────────────────────────────────

class DrawReplacementEffect(BaseModel):
    """A replacement effect for card draw events. CR 614."""
    effect_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    controller: str
    source_permanent_id: str | None = None
    replacement_card_ids: list[str] = Field(default_factory=list)
    once: bool = True
    description: str = ""
    expires: str = "end_of_turn"


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
    Handles: shield counters, regeneration shields, DamagePreventionEffect entries.
    """
    effects: list[ReplacementEffect] = []

    # US4: Active DamagePreventionEffect entries from GameState
    for prev in game_state.prevention_effects:
        if prev.remaining is None or prev.remaining > 0:
            effects.append(ReplacementEffect(
                effect_id=f"prevention_{prev.effect_id}",
                source_permanent_id=prev.source_permanent_id or "",
                controller="",
                description=f"Damage prevention ({prev.remaining} remaining)",
                event_types=["damage"],
                is_self_replacement=False,
            ))

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

    if effect.effect_id.startswith("prevention_") and target_perm:
        # US4: DamagePreventionEffect — reduce damage amount
        prev_id = effect.effect_id[len("prevention_"):]
        prev_effect = next((p for p in game_state.prevention_effects if p.effect_id == prev_id), None)
        if prev_effect is not None:
            damage = event.modified_amount if event.modified_amount is not None else event.amount
            if prev_effect.remaining is None:
                prevented = damage
            else:
                prevented = min(damage, prev_effect.remaining)
                prev_effect.remaining -= prevented
                if prev_effect.remaining <= 0:
                    game_state.prevention_effects[:] = [
                        p for p in game_state.prevention_effects if p.effect_id != prev_id
                    ]
            new_damage = damage - prevented
            if new_damage <= 0:
                event.cancelled = True
            else:
                event.modified_amount = new_damage
            logger.info("Prevention effect reduced damage by %d on %s", prevented, target_perm.card.name)

    elif effect.effect_id.startswith("shield_") and target_perm:
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
    redirect_to_planeswalker_id: str | None = None,
) -> GameState:
    """
    Apply damage through the replacement effect system. REQ-R07, REQ-R08.
    Handles: deathtouch, lifelink, infect (REQ-R12).
    """
    if damage <= 0:
        return game_state

    # US4: Protection from color — prevents damage from matching-color sources
    target_perm_check = next((p for p in game_state.battlefield if p.id == target_id), None)
    if target_perm_check:
        for kw in target_perm_check.card.keywords:
            kw_lower = kw.lower()
            if kw_lower.startswith("protection from "):
                protected_color = kw_lower[len("protection from "):]
                color_map = {
                    "white": "W", "blue": "U", "black": "B",
                    "red": "R", "green": "G",
                }
                prot_abbrev = color_map.get(protected_color)
                if prot_abbrev and prot_abbrev in source_keywords:
                    logger.info(
                        "Protection from %s on %s prevents damage from %s",
                        protected_color, target_perm_check.card.name, source_card_name,
                    )
                    return game_state

    # US17 (T043): Damage redirect to planeswalker — route damage to a planeswalker
    # instead of the player (CR 306.7: attackers may attack planeswalkers)
    effective_target = redirect_to_planeswalker_id if redirect_to_planeswalker_id else target_id

    event = GameEvent(
        event_type="damage",
        source_id=source_card_name,
        target_id=effective_target,
        amount=damage,
        redirect_target_id=redirect_to_planeswalker_id,
    )
    event, game_state = process_event(event, game_state)
    if event.cancelled:
        return game_state

    final_damage = event.modified_amount if event.modified_amount is not None else event.amount
    redirect = event.redirect_target_id or effective_target

    from mtg_engine.ability.keywords.deathtouch import apply_deathtouch_damage_from_card
    from mtg_engine.ability.keywords.infect import (
        apply_infect_damage_to_creature,
        apply_infect_poison_to_player,
    )
    from mtg_engine.ability.keywords.lifelink import apply_lifelink_to_gamestate

    # Apply damage to target permanent
    target_perm = next((p for p in game_state.battlefield if p.id == redirect), None)
    if target_perm and "planeswalker" in target_perm.card.type_line.lower():
        # Damage to a planeswalker reduces its loyalty (CR 306.7) — pure transform
        new_loyalty = max(0, target_perm.loyalty - final_damage)
        new_target = target_perm.model_copy(update={"loyalty": new_loyalty})
        game_state = game_state.model_copy(
            update={
                "battlefield": [
                    new_target if p.id == redirect else p
                    for p in game_state.battlefield
                ]
            }
        )
        logger.info(
            "Planeswalker %s took %d damage (loyalty now %d)",
            target_perm.card.name, final_damage, new_loyalty,
        )
    elif target_perm:
        has_infect = "infect" in source_keywords

        if has_infect:
            # REQ-R12: infect damage to creatures as -1/-1 counters (pure transform)
            game_state = apply_infect_damage_to_creature(
                game_state, target_perm, final_damage
            )
        else:
            # Normal damage: mark damage on creature via model_copy (pure transform)
            new_target = target_perm.model_copy(
                update={"damage_marked": target_perm.damage_marked + final_damage}
            )
            game_state = game_state.model_copy(
                update={
                    "battlefield": [
                        new_target if p.id == redirect else p
                        for p in game_state.battlefield
                    ]
                }
            )

        # Deathtouch tracking (pure transform, no-op if no deathtouch or zero damage)
        game_state = apply_deathtouch_damage_from_card(
            game_state, source_keywords, target_perm.id, final_damage
        )
    else:
        # Target is a player
        for player in game_state.players:
            if player.name == redirect:
                has_infect = "infect" in source_keywords

                if has_infect:
                    # REQ-R12: infect damage to players as poison counters (pure transform)
                    game_state = apply_infect_poison_to_player(
                        game_state, player.name, final_damage
                    )
                else:
                    old_life = player.life
                    new_life = old_life - final_damage
                    # Apply life reduction via model_copy (pure transform)
                    new_player = player.model_copy(update={"life": new_life})
                    game_state = game_state.model_copy(
                        update={
                            "players": [
                                new_player if p.name == redirect else p
                                for p in game_state.players
                            ]
                        }
                    )
                break

    # Lifelink: controller of the SOURCE gains life (REQ-R11) — pure transform
    # Need to find source permanent on battlefield to get controller
    source_perm = next((p for p in game_state.battlefield if p.card.name == source_card_name), None)
    if source_perm and "lifelink" in source_keywords:
        game_state = apply_lifelink_to_gamestate(
            game_state, source_perm, final_damage
        )

    return game_state


# ─── REP-01: Prevention Effect Creation API ─────────────────────────────────

def create_prevention_effect(
    game_state: GameState,
    controller: str,
    amount: int | None = None,
    source_permanent_id: str | None = None,
    target_id: str | None = None,
    combat_only: bool = False,
    expires: str | None = "end_of_turn",
    description: str = "",
) -> GameState:
    """
    Create a damage prevention effect. CR 614.1.

    Args:
        game_state: Current game state
        controller: Player controlling the prevention effect
        amount: Amount of damage to prevent (None = unlimited until end of turn)
        source_permanent_id: Permanent providing the effect
        target_id: Specific permanent to protect (None = global/all combat)
        combat_only: Only prevent combat damage
        expires: Expiry scope ("end_of_turn" or None for persistent)
        description: Human-readable description

    Returns:
        Updated game state with prevention effect added.
    """
    effect = DamagePreventionEffect(
        source_permanent_id=source_permanent_id,
        target_id=target_id,
        remaining=amount,
        combat_only=combat_only,
    )
    if expires:
        effect.extra["expires"] = expires
    if description:
        effect.extra["description"] = description
    game_state.prevention_effects.append(effect)
    logger.info(
        "Prevention effect created for %s: amount=%s, expires=%s",
        controller, amount, expires,
    )
    return game_state


def remove_expired_prevention_effects(
    game_state: GameState,
    expiry_scope: str = "end_of_turn",
) -> GameState:
    """
    Remove prevention effects that have expired.

    Args:
        game_state: Current game state
        expiry_scope: Expiry scope to check ("end_of_turn" by default)

    Returns:
        Updated game state with expired effects removed.
    """
    before = len(game_state.prevention_effects)
    game_state.prevention_effects[:] = [
        eff for eff in game_state.prevention_effects
        if eff.extra.get("expires") != expiry_scope
    ]
    removed = before - len(game_state.prevention_effects)
    if removed:
        logger.info("Removed %d expired prevention effects (scope: %s)", removed, expiry_scope)
    return game_state


# ─── REP-02: Draw Replacement API ───────────────────────────────────────────

def create_draw_replacement(
    game_state: GameState,
    controller: str,
    replacement_card_ids: list[str] | None = None,
    source_permanent_id: str | None = None,
    once: bool = True,
    description: str = "",
    expires: str = "end_of_turn",
) -> GameState:
    """
    Create a draw replacement effect. CR 614.

    Args:
        game_state: Current game state
        controller: Player controlling the replacement
        replacement_card_ids: Card IDs to draw instead
        source_permanent_id: Permanent providing the effect
        once: Consume after one use
        description: Human-readable description
        expires: Expiry scope

    Returns:
        Updated game state with draw replacement added.
    """
    effect = DrawReplacementEffect(
        controller=controller,
        source_permanent_id=source_permanent_id,
        replacement_card_ids=replacement_card_ids or [],
        once=once,
        description=description or f"Draw replacement for {controller}",
        expires=expires,
    )
    game_state.draw_replacements.append(effect)
    logger.info(
        "Draw replacement created for %s: %d replacement cards, once=%s",
        controller, len(effect.replacement_card_ids), once,
    )
    return game_state


def process_draw_event(
    event: GameEvent,
    game_state: GameState,
) -> tuple[GameEvent, GameState]:
    """
    Process a draw event through replacement effects. CR 614.

    Args:
        event: Draw event to process
        game_state: Current game state

    Returns:
        (modified event, updated game state)
    """
    if event.event_type != "draw":
        return event, game_state

    if not game_state.draw_replacements:
        return event, game_state

    # Find applicable replacement for this player
    for i, repl in enumerate(game_state.draw_replacements):
        if repl.controller == event.target_id:
            # Apply replacement
            event.replaced = True
            event.extra["replacement_card_ids"] = repl.replacement_card_ids
            event.extra["replacement_description"] = repl.description
            logger.info(
                "Draw event replaced for %s: %d alternate cards",
                event.target_id, len(repl.replacement_card_ids),
            )

            # Consume if once
            if repl.once:
                game_state.draw_replacements.pop(i)
            break

    return event, game_state
