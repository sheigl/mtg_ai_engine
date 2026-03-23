"""
Combat phase implementation. REQ-A11–REQ-A15.
CR 508-511: declare attackers, declare blockers, combat damage.
CR 702.19: trample. CR 702.2: deathtouch. REQ-R09–REQ-R12.
"""
import logging
from mtg_engine.models.game import (
    GameState, Permanent, AttackerInfo, CombatState, Step, Phase
)
from mtg_engine.models.actions import (
    AttackDeclaration, BlockDeclaration, DamageAssignment
)
from mtg_engine.engine.zones import get_player

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_perm(game_state: GameState, perm_id: str) -> Permanent:
    p = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if p is None:
        raise ValueError(f"Permanent {perm_id!r} not on battlefield")
    return p


def _is_creature(perm: Permanent) -> bool:
    return "creature" in perm.card.type_line.lower()


def _has_keyword(perm: Permanent, kw: str) -> bool:
    return kw in perm.card.keywords


def _effective_power(perm: Permanent) -> int:
    try:
        p = int(perm.card.power or "0")
    except (ValueError, TypeError):
        p = 0
    p += perm.counters.get("+1/+1", 0) - perm.counters.get("-1/-1", 0)
    return max(0, p)


def _effective_toughness(perm: Permanent) -> int:
    try:
        t = int(perm.card.toughness or "0")
    except (ValueError, TypeError):
        t = 0
    t += perm.counters.get("+1/+1", 0) - perm.counters.get("-1/-1", 0)
    return t


def _is_lethal_damage(damage: int, blocker: Permanent, has_deathtouch: bool) -> bool:
    """
    Is `damage` lethal to `blocker`?
    Lethal = damage >= toughness, OR any damage if attacker has deathtouch.
    CR 702.19b, CR 702.2c
    """
    if has_deathtouch:
        return damage > 0
    return damage >= _effective_toughness(blocker)


# ─── Declare Attackers ────────────────────────────────────────────────────────

def declare_attackers(
    game_state: GameState,
    attack_declarations: list[AttackDeclaration],
) -> GameState:
    """
    REQ-A11, CR 508.1.
    Validates and records attacker declarations.
    """
    if game_state.step != Step.DECLARE_ATTACKERS:
        raise ValueError("Not in Declare Attackers step")
    if game_state.priority_holder != game_state.active_player:
        raise ValueError("Active player does not have priority")

    infos: list[AttackerInfo] = []

    for decl in attack_declarations:
        perm = _get_perm(game_state, decl.attacker_id)

        # CR 508.1a: must be a creature, untapped, and either has haste or not summoning sick
        if not _is_creature(perm):
            raise ValueError(f"{perm.card.name} is not a creature")
        if perm.tapped:
            raise ValueError(f"{perm.card.name} is tapped and cannot attack")
        if perm.summoning_sick and not _has_keyword(perm, "haste"):
            raise ValueError(f"{perm.card.name} has summoning sickness")
        if _has_keyword(perm, "defender"):
            raise ValueError(f"{perm.card.name} has defender and cannot attack")

        infos.append(AttackerInfo(
            permanent_id=perm.id,
            defending_id=decl.defending_id,
        ))

        # CR 508.1f: tap the attacker (unless vigilance)
        if not _has_keyword(perm, "vigilance"):
            perm.tapped = True

    game_state.combat = CombatState(attackers=infos)
    return game_state


# ─── Declare Blockers ─────────────────────────────────────────────────────────

def declare_blockers(
    game_state: GameState,
    block_declarations: list[BlockDeclaration],
) -> GameState:
    """
    REQ-A12, CR 509.1.
    Validates and records blocker declarations.
    """
    if game_state.step != Step.DECLARE_BLOCKERS:
        raise ValueError("Not in Declare Blockers step")
    if game_state.combat is None:
        raise ValueError("No active combat state")

    for decl in block_declarations:
        blocker = _get_perm(game_state, decl.blocker_id)

        # CR 509.1a: must be untapped creature
        if not _is_creature(blocker):
            raise ValueError(f"{blocker.card.name} is not a creature")
        if blocker.tapped:
            raise ValueError(f"{blocker.card.name} is tapped and cannot block")

        # Find the attacker info
        attacker_info = next(
            (a for a in game_state.combat.attackers if a.permanent_id == decl.attacker_id),
            None,
        )
        if attacker_info is None:
            raise ValueError(f"{decl.attacker_id!r} is not an attacking creature")

        # CR 702.9 (Flying): can only be blocked by creatures with flying or reach
        attacker = _get_perm(game_state, decl.attacker_id)
        if _has_keyword(attacker, "flying"):
            if not (_has_keyword(blocker, "flying") or _has_keyword(blocker, "reach")):
                raise ValueError(f"{blocker.card.name} cannot block a flying creature")

        attacker_info.is_blocked = True
        attacker_info.blocker_ids.append(blocker.id)
        game_state.combat.blocker_assignments[blocker.id] = decl.attacker_id

    game_state.combat.blockers_declared = True
    return game_state


def order_blockers(
    game_state: GameState,
    attacker_id: str,
    blocker_order: list[str],
) -> GameState:
    """
    REQ-A13, CR 509: When multiple blockers, attacker orders them for damage assignment.
    """
    if game_state.combat is None:
        raise ValueError("No active combat state")
    info = next((a for a in game_state.combat.attackers if a.permanent_id == attacker_id), None)
    if info is None:
        raise ValueError(f"Attacker {attacker_id!r} not found")
    # Validate all blocker IDs in the order list are actual blockers of this attacker
    for bid in blocker_order:
        if bid not in info.blocker_ids:
            raise ValueError(f"{bid!r} is not a blocker of {attacker_id!r}")
    info.blocker_order = blocker_order
    return game_state


# ─── Combat Damage ────────────────────────────────────────────────────────────

def _validate_damage_assignments(
    game_state: GameState,
    assignments: list[DamageAssignment],
) -> None:
    """
    REQ-A15: Validate minimum lethal damage assignment rule. CR 510.1c, CR 702.19b.
    Each blocker must receive at least lethal damage before any excess goes to the player.
    """
    if game_state.combat is None:
        return

    # Group assignments by attacker
    by_attacker: dict[str, dict[str, int]] = {}
    for a in assignments:
        by_attacker.setdefault(a.source_id, {})[a.target_id] = a.damage

    for attacker_info in game_state.combat.attackers:
        try:
            attacker = _get_perm(game_state, attacker_info.permanent_id)
        except ValueError:
            continue  # attacker left battlefield

        attacker_dmg = by_attacker.get(attacker_info.permanent_id, {})
        total_assigned = sum(attacker_dmg.values())
        power = _effective_power(attacker)
        has_trample = _has_keyword(attacker, "trample")
        has_deathtouch = _has_keyword(attacker, "deathtouch")

        if total_assigned > power:
            raise ValueError(
                f"{attacker.card.name} assigns {total_assigned} damage but has power {power}"
            )

        # Check that each blocker gets at least lethal before player gets damage
        player_damage = attacker_dmg.get(attacker_info.defending_id, 0)

        if player_damage > 0 and attacker_info.blocker_ids:
            # Only valid if all blockers have lethal (or attacker has trample)
            if not has_trample:
                raise ValueError(
                    f"{attacker.card.name} is blocked but assigns damage to player without trample"
                )
            # Verify each blocker got lethal
            order = attacker_info.blocker_order or attacker_info.blocker_ids
            for bid in order:
                try:
                    blocker = _get_perm(game_state, bid)
                except ValueError:
                    continue
                blocker_damage = attacker_dmg.get(bid, 0)
                # CR 702.2c: with deathtouch, any nonzero damage is lethal
                if not _is_lethal_damage(blocker_damage, blocker, has_deathtouch):
                    raise ValueError(
                        f"{attacker.card.name}: must assign lethal damage to {blocker.card.name} "
                        f"before trampling over (assigned {blocker_damage}, "
                        f"toughness {_effective_toughness(blocker)})"
                    )


def _auto_assign_damage(game_state: GameState) -> list[DamageAssignment]:
    """
    Auto-generate damage assignments for the current combat state.
    Used when no explicit assignments are provided (e.g. simple cases).
    """
    if game_state.combat is None:
        return []

    assignments: list[DamageAssignment] = []

    for attacker_info in game_state.combat.attackers:
        try:
            attacker = _get_perm(game_state, attacker_info.permanent_id)
        except ValueError:
            continue

        power = _effective_power(attacker)
        has_trample = _has_keyword(attacker, "trample")
        has_deathtouch = _has_keyword(attacker, "deathtouch")

        active_blockers = [
            _get_perm(game_state, bid)
            for bid in (attacker_info.blocker_order or attacker_info.blocker_ids)
            if any(p.id == bid for p in game_state.battlefield)
        ]

        if not active_blockers:
            # Unblocked: all damage to defending player/planeswalker (CR 510.1b)
            assignments.append(DamageAssignment(
                source_id=attacker_info.permanent_id,
                target_id=attacker_info.defending_id,
                damage=power,
            ))
        else:
            # Assign damage to blockers in order, then trample excess to player
            remaining = power
            for i, blocker in enumerate(active_blockers):
                if remaining <= 0:
                    break
                # CR 702.2c: deathtouch — 1 damage is lethal
                lethal_needed = 1 if has_deathtouch else max(0, _effective_toughness(blocker))
                is_last = (i == len(active_blockers) - 1)

                if has_trample:
                    # With trample: assign exactly lethal to each blocker, excess goes to player
                    to_assign = min(remaining, lethal_needed)
                else:
                    # Without trample: pile all remaining damage into blockers
                    to_assign = remaining if is_last else min(remaining, lethal_needed)

                assignments.append(DamageAssignment(
                    source_id=attacker_info.permanent_id,
                    target_id=blocker.id,
                    damage=to_assign,
                ))
                remaining -= to_assign

            # Trample: remaining damage goes to defending player (REQ-R09, CR 702.19b)
            if has_trample and remaining > 0:
                assignments.append(DamageAssignment(
                    source_id=attacker_info.permanent_id,
                    target_id=attacker_info.defending_id,
                    damage=remaining,
                ))

    return assignments


def assign_combat_damage(
    game_state: GameState,
    assignments: list[DamageAssignment] | None = None,
) -> GameState:
    """
    REQ-A14, REQ-A15. Apply combat damage step. CR 510.
    If assignments is None, auto-assigns damage.
    Handles first/double strike (CR 510.4).
    """
    if game_state.combat is None:
        return game_state

    # Auto-assign if not provided or empty (engine handles CR 510.1 automatically)
    if not assignments:
        assignments = _auto_assign_damage(game_state)
    else:
        _validate_damage_assignments(game_state, assignments)

    # Mark damage as assigned for this step so the action isn't re-offered
    game_state.combat.damage_assigned = True

    # Also generate blocker assignments (blockers deal damage back to attackers)
    blocker_assignments = _generate_blocker_damage(game_state)

    all_assignments = assignments + blocker_assignments

    # CR 510.2: all damage dealt simultaneously
    for assign in all_assignments:
        try:
            source = _get_perm(game_state, assign.source_id)
        except ValueError:
            continue

        has_deathtouch = _has_keyword(source, "deathtouch")
        has_lifelink   = _has_keyword(source, "lifelink")
        has_infect     = _has_keyword(source, "infect")

        # Deal damage to target
        target_perm = next((p for p in game_state.battlefield if p.id == assign.target_id), None)
        if target_perm:
            if has_infect:
                # REQ-R12: infect damage to creatures as -1/-1 counters
                target_perm.counters["-1/-1"] = target_perm.counters.get("-1/-1", 0) + assign.damage
            else:
                target_perm.damage_marked += assign.damage
            if has_deathtouch and assign.damage > 0:
                # REQ-R10: mark for deathtouch SBA (CR 702.2b)
                target_perm.counters["__deathtouch_damage__"] = (
                    target_perm.counters.get("__deathtouch_damage__", 0) + assign.damage
                )
        else:
            # Target is a player
            for player in game_state.players:
                if player.name == assign.target_id:
                    if has_infect:
                        # REQ-R12: infect damage to players as poison counters
                        player.poison_counters += assign.damage
                    else:
                        player.life -= assign.damage
                        # Commander damage tracking: record if attacker is a commander
                        if game_state.format == "commander" and assign.damage > 0:
                            controller = get_player(game_state, source.controller)
                            if controller.commander_name and source.card.name == controller.commander_name:
                                if source.id not in game_state.commander_damage:
                                    game_state.commander_damage[source.id] = {}
                                prev = game_state.commander_damage[source.id].get(player.name, 0)
                                game_state.commander_damage[source.id][player.name] = prev + assign.damage
                    break

        # Lifelink: source controller gains life (REQ-R11)
        if has_lifelink and assign.damage > 0:
            controller = get_player(game_state, source.controller)
            controller.life += assign.damage

    return game_state


def _generate_blocker_damage(game_state: GameState) -> list[DamageAssignment]:
    """Generate damage from blocking creatures back to their attackers. CR 510.1d"""
    if game_state.combat is None:
        return []
    assignments: list[DamageAssignment] = []
    # Map blocker_id → list of attacker_ids
    assigned_by: dict[str, list[str]] = {}
    for attacker_info in game_state.combat.attackers:
        for bid in attacker_info.blocker_ids:
            assigned_by.setdefault(bid, []).append(attacker_info.permanent_id)

    for bid, attacker_ids in assigned_by.items():
        blocker = next((p for p in game_state.battlefield if p.id == bid), None)
        if blocker is None:
            continue
        power = _effective_power(blocker)
        # Divide evenly among attackers (simplified)
        per_attacker = power // len(attacker_ids) if attacker_ids else 0
        for aid in attacker_ids:
            if per_attacker > 0:
                assignments.append(DamageAssignment(
                    source_id=bid,
                    target_id=aid,
                    damage=per_attacker,
                ))
    return assignments


def has_first_strike_combatants(game_state: GameState) -> bool:
    """CR 510.4: Check if any attacker/blocker has first strike or double strike."""
    if game_state.combat is None:
        return False
    for info in game_state.combat.attackers:
        perm = next((p for p in game_state.battlefield if p.id == info.permanent_id), None)
        if perm and (_has_keyword(perm, "first strike") or _has_keyword(perm, "double strike")):
            return True
        for bid in info.blocker_ids:
            bp = next((p for p in game_state.battlefield if p.id == bid), None)
            if bp and (_has_keyword(bp, "first strike") or _has_keyword(bp, "double strike")):
                return True
    return False


def end_combat(game_state: GameState) -> GameState:
    """CR 511.3: Remove all creatures from combat, clear combat state."""
    game_state.combat = None
    return game_state
