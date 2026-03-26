"""
State-Based Actions. REQ-R01.
CR 704: checked before every priority grant, loop until no more apply.
"""
import logging
from collections import defaultdict
from dataclasses import dataclass, field

from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)


@dataclass
class SBAEvent:
    """Record of a single SBA that was applied."""
    sba_type: str
    description: str
    affected_ids: list[str] = field(default_factory=list)


def check_and_apply_sbas(game_state: GameState) -> tuple[GameState, list[SBAEvent]]:
    """
    Run SBA check loop: apply all applicable SBAs, repeat until none fire.
    REQ-R01: called before every priority grant.
    Returns updated game_state and list of SBAEvents that occurred.
    CR 704: loop until a complete pass fires no SBAs.
    """
    all_events: list[SBAEvent] = []
    while True:
        game_state, events = _check_once(game_state)
        if not events:
            break
        all_events.extend(events)
    return game_state, all_events


def _check_once(game_state: GameState) -> tuple[GameState, list[SBAEvent]]:
    """Run one pass of all SBA checks. Returns events from this pass."""
    events: list[SBAEvent] = []

    # CR 704.5a: player at 0 or less life loses
    for p in game_state.players:
        if not p.has_lost and p.life <= 0:
            p.has_lost = True
            events.append(SBAEvent("life_loss", f"{p.name} has 0 or less life and loses", [p.name]))

    # CR 704.5c: 10 or more poison counters → player loses
    for p in game_state.players:
        if not p.has_lost and p.poison_counters >= 10:
            p.has_lost = True
            events.append(SBAEvent("poison", f"{p.name} has 10+ poison counters and loses", [p.name]))

    # Commander damage SBA: 21+ damage from a single commander → player loses
    if game_state.format == "commander":
        for perm_id, damage_by_player in game_state.commander_damage.items():
            for defender_name, total in damage_by_player.items():
                player = next((p for p in game_state.players if p.name == defender_name), None)
                if player and total >= 21 and not player.has_lost:
                    player.has_lost = True
                    events.append(SBAEvent(
                        "commander_damage",
                        f"{defender_name} has taken 21+ commander damage from {perm_id} and loses",
                        [defender_name],
                    ))

    # CR 704.5d: tokens in non-battlefield zones cease to exist
    for p in game_state.players:
        p.graveyard[:] = [c for c in p.graveyard if not getattr(c, "is_token", False)]
        p.hand[:] = [c for c in p.hand if not getattr(c, "is_token", False)]
        p.exile[:] = [c for c in p.exile if not getattr(c, "is_token", False)]

    # CR 704.5f: creature with toughness ≤ 0 → graveyard (regeneration cannot replace)
    to_remove: list[Permanent] = []
    for perm in game_state.battlefield:
        if _is_creature(perm):
            toughness = _effective_toughness(perm)
            if toughness is not None and toughness <= 0:
                to_remove.append(perm)
    for perm in to_remove:
        game_state = _destroy_permanent(game_state, perm)
        events.append(SBAEvent("toughness_zero", f"{perm.card.name} has toughness ≤0", [perm.id]))

    # CR 704.5g: creature with lethal damage (damage ≥ toughness) → destroyed
    # (regeneration can replace; indestructible prevents) REQ-R07
    to_remove = []
    for perm in game_state.battlefield:
        if _is_creature(perm) and not _is_indestructible(perm):
            toughness = _effective_toughness(perm)
            if toughness is not None and toughness > 0 and perm.damage_marked >= toughness:
                to_remove.append(perm)
    for perm in to_remove:
        game_state = _destroy_permanent(game_state, perm)
        events.append(SBAEvent("lethal_damage", f"{perm.card.name} has lethal damage", [perm.id]))

    # CR 704.5h: creature dealt damage by a deathtouch source → destroyed (REQ-R10)
    # Tracked via "__deathtouch_damage__" counter on the permanent
    to_remove = []
    for perm in game_state.battlefield:
        if _is_creature(perm) and not _is_indestructible(perm):
            if perm.counters.get("__deathtouch_damage__", 0) > 0:
                to_remove.append(perm)
    for perm in to_remove:
        perm.counters.pop("__deathtouch_damage__", None)
        game_state = _destroy_permanent(game_state, perm)
        events.append(SBAEvent("deathtouch", f"{perm.card.name} destroyed by deathtouch", [perm.id]))

    # CR 704.5i: planeswalker with 0 loyalty counters → graveyard
    to_remove = []
    for perm in game_state.battlefield:
        if _is_planeswalker(perm):
            loyalty = perm.counters.get("loyalty", 0)
            if loyalty <= 0:
                to_remove.append(perm)
    for perm in to_remove:
        game_state = _move_to_graveyard(game_state, perm)
        events.append(SBAEvent("planeswalker_loyalty", f"{perm.card.name} has 0 loyalty", [perm.id]))

    # CR 704.5j: legend rule — same controller, same legendary permanent name → keep one
    legend_groups: dict[str, list[Permanent]] = defaultdict(list)
    for perm in game_state.battlefield:
        if "legendary" in perm.card.type_line.lower():
            key = f"{perm.controller}::{perm.card.name}"
            legend_groups[key].append(perm)
    for key, perms in legend_groups.items():
        if len(perms) > 1:
            # Keep the one with the latest timestamp (most recently entered); sacrifice the rest
            perms.sort(key=lambda p: p.timestamp)
            for perm in perms[:-1]:
                game_state = _move_to_graveyard(game_state, perm)
                events.append(SBAEvent("legend_rule", f"Legend rule: {perm.card.name} sacrificed", [perm.id]))

    # CR 704.5m: Aura not attached to a legal permanent → graveyard
    to_remove = []
    for perm in game_state.battlefield:
        if "aura" in perm.card.type_line.lower():
            if not perm.attached_to:
                to_remove.append(perm)
            else:
                target_exists = any(p.id == perm.attached_to for p in game_state.battlefield)
                if not target_exists:
                    to_remove.append(perm)
    for perm in to_remove:
        game_state = _move_to_graveyard(game_state, perm)
        events.append(SBAEvent("aura_illegal", f"{perm.card.name} aura has no legal enchanted object", [perm.id]))

    # CR 704.5n: Equipment attached to illegal permanent → becomes unattached (stays on battlefield)
    for perm in game_state.battlefield:
        if "equipment" in perm.card.type_line.lower() and perm.attached_to:
            target_exists = any(
                p.id == perm.attached_to and _is_creature(p)
                for p in game_state.battlefield
            )
            if not target_exists:
                perm.attached_to = None
                events.append(SBAEvent("equipment_detach", f"{perm.card.name} detached", [perm.id]))

    # CR 704.5q: +1/+1 and -1/-1 counters annihilate each other (REQ-R14)
    for perm in game_state.battlefield:
        plus = perm.counters.get("+1/+1", 0)
        minus = perm.counters.get("-1/-1", 0)
        if plus > 0 and minus > 0:
            n = min(plus, minus)
            perm.counters["+1/+1"] = plus - n
            perm.counters["-1/-1"] = minus - n
            if perm.counters["+1/+1"] == 0:
                del perm.counters["+1/+1"]
            if perm.counters["-1/-1"] == 0:
                del perm.counters["-1/-1"]
            events.append(SBAEvent(
                "counter_annihilation",
                f"{n} +1/+1 and -1/-1 counter pair(s) annihilated on {perm.card.name}",
                [perm.id],
            ))

    # Check if game is over after all SBAs applied
    losers = [p for p in game_state.players if p.has_lost]
    if losers and not game_state.is_game_over:
        game_state.is_game_over = True
        winners = [p for p in game_state.players if not p.has_lost]
        game_state.winner = winners[0].name if winners else None

    return game_state, events


# --- Helpers ---

def _is_creature(perm: Permanent) -> bool:
    """Return True if the permanent is a creature."""
    return "creature" in perm.card.type_line.lower()


def _is_planeswalker(perm: Permanent) -> bool:
    """Return True if the permanent is a planeswalker."""
    return "planeswalker" in perm.card.type_line.lower()


def _is_indestructible(perm: Permanent) -> bool:
    """Return True if the permanent has the indestructible keyword."""
    return "indestructible" in perm.card.keywords


def _effective_toughness(perm: Permanent) -> int | None:
    """
    Get effective toughness including +1/+1 and -1/-1 counters.
    Returns None if toughness cannot be determined (e.g., non-creature).
    """
    base = perm.card.toughness
    if base is None:
        return None
    try:
        t = int(base)
    except (ValueError, TypeError):
        return None
    t += perm.counters.get("+1/+1", 0)
    t -= perm.counters.get("-1/-1", 0)
    t += perm.toughness_bonus
    return t


def _destroy_permanent(game_state: GameState, perm: Permanent) -> GameState:
    """Move permanent to its controller's graveyard (destruction)."""
    from mtg_engine.engine.zones import move_permanent_to_zone
    return move_permanent_to_zone(game_state, perm, "graveyard")


def _move_to_graveyard(game_state: GameState, perm: Permanent) -> GameState:
    """Move permanent to its controller's graveyard (non-destruction, e.g., SBA)."""
    from mtg_engine.engine.zones import move_permanent_to_zone
    return move_permanent_to_zone(game_state, perm, "graveyard")
