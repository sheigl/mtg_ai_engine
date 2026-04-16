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
from mtg_engine.engine.turn_manager import begin_step

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
    p += perm.power_bonus
    return max(0, p)


def _effective_toughness(perm: Permanent) -> int:
    try:
        t = int(perm.card.toughness or "0")
    except (ValueError, TypeError):
        t = 0
    t += perm.counters.get("+1/+1", 0) - perm.counters.get("-1/-1", 0)
    t += perm.toughness_bonus
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


def _has_hexproof_or_shroud(perm: Permanent) -> bool:
    """Check if a permanent has hexproof or shroud."""
    return _has_keyword(perm, "hexproof") or _has_keyword(perm, "shroud")


def _has_protection(perm: Permanent, from_keyword: str) -> bool:
    """Check if a permanent has protection from a specific keyword."""
    return any(f"protection from {from_keyword}" in kw.lower() for kw in perm.card.keywords)


def _has_protection_from(perm: Permanent, quality: str) -> bool:
    """
    Check if a permanent has protection from a specific quality.
    Quality can be: color (W/U/B/R/G), type (creature/enchantment/etc), 
    CMC number, controller, or "everything".
    """
    if not quality:
        return False
    
    quality_lower = quality.lower()
    
    # "Protection from everything"
    if quality_lower == "everything":
        return any("protection from everything" in kw.lower() for kw in perm.card.keywords)
    
    # Color protection
    if quality_lower in {"white", "blue", "black", "red", "green", "w", "u", "b", "r", "g"}:
        color_map = {
            "white": "white", "w": "white",
            "blue": "blue", "u": "blue",
            "black": "black", "b": "black",
            "red": "red", "r": "red",
            "green": "green", "g": "green",
        }
        color = color_map.get(quality_lower)
        if color:
            return any(f"protection from {color}" in kw.lower() for kw in perm.card.keywords)
    
    # Type protection (creature, enchantment, land, etc.)
    return any(f"protection from {quality_lower}" in kw.lower() for kw in perm.card.keywords)


def _get_protection_qualities(perm: Permanent) -> list[str]:
    """
    Extract all qualities from a permanent's protection keywords.
    Returns a list of qualities like ["white", "creature", "everything"].
    """
    qualities = []
    for kw in perm.card.keywords:
        kw_lower = kw.lower()
        if kw_lower.startswith("protection from "):
            quality = kw_lower.replace("protection from ", "")
            if quality:
                qualities.append(quality)
    return qualities


def _get_source_qualities(
    source_card: Any,
    source_controller: str,
    target_controller: str,
) -> list[str]:
    """
    Determine what qualities a source has for protection targeting checks (CR 702.16).
    
    Returns a list of qualities that the source has:
    - Colors from mana cost
    - Types from type line
    - Controller if source is a player's permanent
    - CMC if relevant
    """
    qualities = []
    
    # Color qualities from mana cost
    if source_card.mana_cost:
        colors = []
        mana_lower = source_card.mana_cost.lower()
        if "w" in mana_lower or "{w}" in mana_lower:
            colors.append("white")
        if "u" in mana_lower or "{u}" in mana_lower:
            colors.append("blue")
        if "b" in mana_lower or "{b}" in mana_lower:
            colors.append("black")
        if "r" in mana_lower or "{r}" in mana_lower:
            colors.append("red")
        if "g" in mana_lower or "{g}" in mana_lower:
            colors.append("green")
        qualities.extend(colors)
    
    # Type qualities from type line
    if source_card.type_line:
        type_line_lower = source_card.type_line.lower()
        # Check if it's a spell/ability from a creature
        if "creature" in type_line_lower:
            qualities.append("creature")
        # Check for other types that could be protection targets
        for card_type in ["enchantment", "artifact", "land", "planeswalker"]:
            if card_type in type_line_lower:
                qualities.append(card_type)
    
    # Source controller as a quality (for "protection from opponents" etc.)
    if source_controller != target_controller:
        qualities.append("opponent")
    
    return qualities


# Landwalk keyword → land subtype mapping (CR 702.11)
_LANDWALK_MAP = {
    "islandwalk": "island",
    "swampwalk": "swamp",
    "mountainwalk": "mountain",
    "forestwalk": "forest",
    "plainswalk": "plains",
}


def _check_landwalk(
    game_state: GameState,
    attacker: Permanent,
    blocker: Permanent,
    defending_player_name: str,
) -> None:
    """
    CR 702.11: Landwalk — if attacker has [type]walk and defending player controls a land
    of that type, the attacker cannot be blocked. Raises ValueError if block is illegal.
    """
    for kw in attacker.card.keywords:
        kw_lower = kw.lower()
        land_type = _LANDWALK_MAP.get(kw_lower)
        if land_type:
            # Check if defending player controls a land of this type
            controls_land = any(
                p.controller == defending_player_name
                and "land" in p.card.type_line.lower()
                and land_type in p.card.type_line.lower()
                for p in game_state.battlefield
            )
            if controls_land:
                raise ValueError(
                    f"{attacker.card.name} has {kw} — cannot be blocked while defending player "
                    f"controls a {land_type}"
                )


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

    # After attackers are declared, advance to DECLARE_BLOCKERS step.
    # (First-strike check happens in declare_blockers, after blockers are known.)
    game_state.step = Step.DECLARE_BLOCKERS
    game_state = begin_step(game_state)

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

        # US6: Check BlockConstraint (cannot_block)
        for con in game_state.block_constraints:
            if con.constraint_type == "cannot_block" and con.affected_id in (blocker.id, "all"):
                raise ValueError(f"{blocker.card.name} cannot block due to an active restriction")

        # US6: Goaded creatures cannot block (CR 702.117b)
        if any(k.startswith("goad_by_") for k in blocker.counters):
            raise ValueError(f"{blocker.card.name} is goaded and cannot block")

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

        # US19 CR 702.16c: Protection "Blocking" — creature with protection from X
        # cannot be blocked by X creatures
        blocker_colors = [c.lower() for c in blocker.card.colors]
        for kw in attacker.card.keywords:
            kw_lower = kw.lower()
            if kw_lower.startswith("protection from "):
                protected_from = kw_lower[len("protection from "):]
                if protected_from in blocker_colors:
                    raise ValueError(
                        f"{blocker.card.name} cannot block {attacker.card.name} "
                        f"(protection from {protected_from})"
                    )

        # US21 CR 702.27 (Shadow): shadow creatures can only be blocked by shadow creatures,
        # and shadow creatures can only block shadow creatures
        attacker_has_shadow = _has_keyword(attacker, "shadow")
        blocker_has_shadow = _has_keyword(blocker, "shadow")
        if attacker_has_shadow and not blocker_has_shadow:
            raise ValueError(f"{blocker.card.name} cannot block a shadow creature without shadow")
        if blocker_has_shadow and not attacker_has_shadow:
            raise ValueError(f"{blocker.card.name} (shadow) cannot block a non-shadow creature")

        # US21 CR 702.54 (Horsemanship): same as flying but for horsemanship
        if _has_keyword(attacker, "horsemanship"):
            if not _has_keyword(blocker, "horsemanship"):
                raise ValueError(f"{blocker.card.name} cannot block a creature with horsemanship")

        # US21 CR 702.11 (Landwalk): if attacker has [type]walk and defending player controls
        # a land of that type, the attacker is unblockable
        defending_player_name = next(
            (p.name for p in game_state.players if p.name != game_state.active_player), ""
        )
        _check_landwalk(game_state, attacker, blocker, defending_player_name)

        # US2: Menace enforcement — attacker with menace requires 2+ blockers
        if _has_keyword(attacker, "menace"):
            existing_blockers = len(attacker_info.blocker_ids)
            blockers_for_this_attacker = sum(
                1 for d in block_declarations if d.attacker_id == decl.attacker_id
            )
            if existing_blockers == 0 and blockers_for_this_attacker == 1:
                raise ValueError(f"{attacker.card.name} has menace and must be blocked by 2+ creatures")

        attacker_info.is_blocked = True
        attacker_info.blocker_ids.append(blocker.id)
        game_state.combat.blocker_assignments[blocker.id] = decl.attacker_id

    game_state.combat.blockers_declared = True

    # US3 (T008): After blockers are declared, check for first-strike combatants
    # and transition to the appropriate damage step.
    if has_first_strike_combatants(game_state):
        game_state.step = Step.FIRST_STRIKE_DAMAGE
    else:
        game_state.step = Step.COMBAT_DAMAGE
    game_state = begin_step(game_state)

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


def _auto_assign_damage(game_state: GameState, first_strike_only: bool = False) -> list[DamageAssignment]:
    """
    Auto-generate damage assignments for the current combat state.
    Used when no explicit assignments are provided (e.g. simple cases).
    
    When first_strike_only=True: only creatures with first strike or double strike deal damage
    When first_strike_only=False: only creatures WITHOUT first-strike-only deal damage
    """
    if game_state.combat is None:
        return []

    assignments: list[DamageAssignment] = []

    for attacker_info in game_state.combat.attackers:
        try:
            attacker = _get_perm(game_state, attacker_info.permanent_id)
        except ValueError:
            continue

        # Filter attackers based on first_strike_only parameter
        if first_strike_only:
            # Only include attackers with first strike or double strike
            if not (_has_keyword(attacker, "first strike") or _has_keyword(attacker, "double strike")):
                continue
        else:
            # Only include attackers without first strike or double strike
            if _has_keyword(attacker, "first strike") or _has_keyword(attacker, "double strike"):
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
    first_strike_only: bool = False,
) -> GameState:
    """
    REQ-A14, REQ-A15. Apply combat damage step. CR 510.
    If assignments is None, auto-assigns damage.
    Handles first/double strike (CR 510.4).
    
    When first_strike_only=True: only creatures with first strike or double strike deal damage
    When first_strike_only=False: only creatures WITHOUT first-strike-only deal damage
    """
    if game_state.combat is None:
        return game_state

    # Idempotent guard: if damage was already assigned this step, skip
    # (prevents double-damage when begin_step auto-assigns and API calls again)
    if game_state.combat.damage_assigned:
        return game_state

    # US4: Fog-style prevention — prevent all combat damage this turn
    if game_state.prevent_all_combat_damage:
        game_state.combat.damage_assigned = True
        game_state.prevent_all_combat_damage = False
        logger.info("All combat damage prevented (Fog effect active)")
        return game_state

    # Auto-assign if not provided or empty (engine handles CR 510.1 automatically)
    if not assignments:
        assignments = _auto_assign_damage(game_state, first_strike_only)
    else:
        _validate_damage_assignments(game_state, assignments)

    # Mark damage as assigned for this step so the action isn't re-offered
    game_state.combat.damage_assigned = True

    # Also generate blocker assignments (blockers deal damage back to attackers)
    blocker_assignments = _generate_blocker_damage(game_state)

    all_assignments = assignments + blocker_assignments

    # CR 510.2: all damage dealt simultaneously
    # Check combat damage triggers (US2: "whenever this deals combat damage to a player")
    from mtg_engine.engine.triggers import check_damage_triggers
    game_state = check_damage_triggers(game_state, all_assignments)

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
            is_planeswalker_target = "planeswalker" in target_perm.card.type_line.lower()
            if is_planeswalker_target:
                # CR 306.6: combat damage to planeswalker reduces loyalty (not damage_marked)
                target_perm.loyalty = max(0, target_perm.loyalty - assign.damage)
            elif has_infect:
                # REQ-R12: infect damage to creatures as -1/-1 counters
                target_perm.counters["-1/-1"] = target_perm.counters.get("-1/-1", 0) + assign.damage
            else:
                target_perm.damage_marked += assign.damage
            if has_deathtouch and assign.damage > 0 and not is_planeswalker_target:
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
