"""
Attack requirements and restrictions.

CMB-01: Implements attack restrictions/requirements including:
- "Must attack" (CR 508.2): Creatures that must attack if able
- "Must attack with all creatures" (Propaganda-style)
- "Cannot attack alone" (Partner keyword)
- "Attacks alone" (Raid boss / attacks alone)
- Additional attack cost requirements
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent, AttackConstraint

logger = logging.getLogger(__name__)

# Oracle text patterns for attack requirements
_MUST_ATTACK_PATTERNS = [
    re.compile(r"creatures you control must attack (?:if able)?", re.IGNORECASE),
    re.compile(r"(?:this|~)(?: creature)? must attack (?:if able)?", re.IGNORECASE),
    re.compile(r"you must attack with (?:all )?creatures (?:you control)? (?:if able)?", re.IGNORECASE),
    re.compile(r"creatures with power (\d+) or greater must attack", re.IGNORECASE),
]

_ATTACKS_ALONE_PATTERNS = [
    re.compile(r"(?:this|~)(?: creature)? attacks? alone", re.IGNORECASE),
]

_CANT_ATTACK_ALONE_PATTERNS = [
    re.compile(r"(?:this|~)(?: creature)? cannot attack alone", re.IGNORECASE),
]


def check_must_attack_requirements(
    game_state: GameState,
    attacker_ids: list[str],
) -> list[str]:
    """
    Check which creatures must attack but are not declared.

    CR 508.2: If any effects say that a creature must attack, it must be
    included in the attack declaration (unless it can't attack).

    Args:
        game_state: Current game state.
        attacker_ids: List of permanent IDs declared as attackers.

    Returns:
        List of error messages for creatures that must attack but don't.
    """
    errors: list[str] = []
    attacker_set = set(attacker_ids)

    # Check attack constraints for must_attack
    for constraint in game_state.attack_constraints:
        if constraint.constraint_type != "must_attack":
            continue

        if constraint.affected_id == "all":
            # All creatures controlled by the constraint source's controller must attack
            source_perm = next(
                (p for p in game_state.battlefield if p.id == constraint.source_id),
                None,
            )
            if not source_perm:
                continue
            controller = source_perm.controller

            for perm in game_state.battlefield:
                if perm.controller != controller:
                    continue
                if "creature" not in perm.card.type_line.lower():
                    continue
                if perm.id in attacker_set:
                    continue
                if not _can_attack(perm):
                    continue
                errors.append(
                    f"{perm.card.name} must attack due to "
                    f"active must-attack constraint"
                )
        else:
            # Specific creature must attack
            perm = next(
                (p for p in game_state.battlefield if p.id == constraint.affected_id),
                None,
            )
            if perm and perm.id not in attacker_set:
                if _can_attack(perm):
                    errors.append(
                        f"{perm.card.name} must attack due to "
                        f"active must-attack constraint"
                    )

    # Check for "attacks alone" — if a creature attacks alone, no other
    # creatures controlled by that player can attack
    for perm in game_state.battlefield:
        if perm.id not in attacker_set:
            continue
        if _has_attacks_alone(perm):
            controller = perm.controller
            other_attackers = [
                p for p in game_state.battlefield
                if p.controller == controller
                and p.id != perm.id
                and p.id in attacker_set
            ]
            if other_attackers:
                errors.append(
                    f"{perm.card.name} attacks alone — "
                    f"{len(other_attackers)} other creature(s) cannot attack"
                )

    return errors


def check_cannot_attack_restrictions(
    game_state: GameState,
    perm: Permanent,
) -> list[str]:
    """
    Check if a creature has restrictions preventing it from attacking.

    Args:
        game_state: Current game state.
        perm: The creature to check.

    Returns:
        List of error messages for each restriction that prevents attacking.
    """
    errors: list[str] = []

    # Check attack constraints for cannot_attack
    for constraint in game_state.attack_constraints:
        if constraint.constraint_type != "cannot_attack":
            continue
        if constraint.affected_id in (perm.id, "all"):
            source_perm = next(
                (p for p in game_state.battlefield if p.id == constraint.source_id),
                None,
            )
            source_name = source_perm.card.name if source_perm else "unknown"
            errors.append(
                f"{perm.card.name} cannot attack due to {source_name}"
            )

    # Check for "defender" keyword (already in combat.py but included for completeness)
    if "defender" in (perm.card.keywords or []):
        errors.append(f"{perm.card.name} has defender and cannot attack")

    return errors


def check_cannot_attack_alone(
    game_state: GameState,
    perm: Permanent,
    attacker_ids: list[str],
) -> bool:
    """
    Check if a creature that cannot attack alone is attacking alone.

    Args:
        game_state: Current game state.
        perm: The creature to check.
        attacker_ids: List of declared attacker IDs.

    Returns:
        True if the creature is illegally attacking alone.
    """
    if perm.id not in attacker_ids:
        return False

    controller = perm.controller
    same_controller_attackers = [
        p for p in game_state.battlefield
        if p.controller == controller and p.id in attacker_ids
    ]

    has_cant_attack_alone = _has_cannot_attack_alone(perm)
    if has_cant_attack_alone and len(same_controller_attackers) < 2:
        return True

    return False


def parse_attack_requirements(
    oracle_text: str,
) -> list[dict]:
    """
    Parse attack requirement patterns from oracle text.

    Args:
        oracle_text: Card's oracle text.

    Returns:
        List of requirement dicts with 'type' and 'details'.
    """
    requirements: list[dict] = []

    for pattern in _MUST_ATTACK_PATTERNS:
        match = pattern.search(oracle_text)
        if match:
            requirements.append({
                "type": "must_attack",
                "pattern": pattern.pattern,
                "groups": match.groups(),
            })

    for pattern in _ATTACKS_ALONE_PATTERNS:
        match = pattern.search(oracle_text)
        if match:
            requirements.append({
                "type": "attacks_alone",
                "pattern": pattern.pattern,
            })

    for pattern in _CANT_ATTACK_ALONE_PATTERNS:
        match = pattern.search(oracle_text)
        if match:
            requirements.append({
                "type": "cannot_attack_alone",
                "pattern": pattern.pattern,
            })

    return requirements


def create_must_attack_constraint(
    source_perm: Permanent,
    affected_id: str = "all",
) -> "AttackConstraint":
    """
    Create an AttackConstraint for a must-attack effect.

    Args:
        source_perm: The permanent creating the constraint.
        affected_id: Permanent ID or "all" for all creatures.

    Returns:
        AttackConstraint ready to add to game_state.attack_constraints.
    """
    from mtg_engine.models.game import AttackConstraint

    return AttackConstraint(
        source_id=source_perm.id,
        affected_id=affected_id,
        constraint_type="must_attack",
    )


def create_cannot_attack_constraint(
    source_perm: Permanent,
    affected_id: str = "all",
) -> "AttackConstraint":
    """
    Create an AttackConstraint for a cannot-attack effect.

    Args:
        source_perm: The permanent creating the constraint.
        affected_id: Permanent ID or "all" for all creatures.

    Returns:
        AttackConstraint ready to add to game_state.attack_constraints.
    """
    from mtg_engine.models.game import AttackConstraint

    return AttackConstraint(
        source_id=source_perm.id,
        affected_id=affected_id,
        constraint_type="cannot_attack",
    )


# ─── Private helpers ──────────────────────────────────────────────────────────


def _can_attack(perm: Permanent) -> bool:
    """Check if a creature is physically able to attack."""
    if "creature" not in perm.card.type_line.lower():
        return False
    if perm.tapped:
        return False
    if perm.summoning_sick and "haste" not in (perm.card.keywords or []):
        return False
    if "defender" in (perm.card.keywords or []):
        return False
    return True


def _has_attacks_alone(perm: Permanent) -> bool:
    """Check if a permanent has the attacks alone ability."""
    oracle = perm.card.oracle_text or ""
    return any(p.search(oracle) for p in _ATTACKS_ALONE_PATTERNS)


def _has_cannot_attack_alone(perm: Permanent) -> bool:
    """Check if a permanent cannot attack alone."""
    oracle = perm.card.oracle_text or ""
    return any(p.search(oracle) for p in _CANT_ATTACK_ALONE_PATTERNS)
