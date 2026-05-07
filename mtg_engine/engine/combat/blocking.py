"""
Blocking restrictions and abilities.

CMB-02: Implements cannot-block abilities:
- "Cannot block" (CR 509.1)
- "Can't be blocked" (unblockable)
- Keyword-based blocking restrictions

CMB-05: Implements multi-block restrictions:
- "Can only block <type>" (e.g., "can only block flying creatures")
- "Can only block creatures with power N or less"
- Shadow-style blocking restrictions
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent, BlockConstraint

logger = logging.getLogger(__name__)

# Oracle text patterns for blocking restrictions
_CANNOT_BLOCK_PATTERNS = [
    re.compile(r"(?:this|~)(?: creature)? cannot block", re.IGNORECASE),
    re.compile(r"creatures you control cannot block", re.IGNORECASE),
    re.compile(r"(?:this|~)(?: creature)? can't block", re.IGNORECASE),
]

_CAN_ONLY_BLOCK_PATTERNS = [
    re.compile(r"(?:this|~)(?: creature)? can only block (\w+) creatures?", re.IGNORECASE),
    re.compile(r"(?:this|~)(?: creature)? can only block creatures with (\w+)", re.IGNORECASE),
]

_UNBLOCKABLE_PATTERNS = [
    re.compile(r"(?:this|~)(?: creature)? can't be blocked", re.IGNORECASE),
    re.compile(r"(?:this|~)(?: creature)? cannot be blocked", re.IGNORECASE),
]


def check_cannot_block(
    game_state: GameState,
    blocker: Permanent,
) -> list[str]:
    """
    Check if a creature is prevented from blocking by any restriction.

    Args:
        game_state: Current game state.
        blocker: The creature attempting to block.

    Returns:
        List of error messages for each restriction.
    """
    errors: list[str] = []

    # Check block constraints
    for constraint in game_state.block_constraints:
        if constraint.constraint_type == "cannot_block":
            if constraint.affected_id in (blocker.id, "all"):
                source_perm = next(
                    (p for p in game_state.battlefield if p.id == constraint.source_id),
                    None,
                )
                source_name = source_perm.card.name if source_perm else "unknown"
                errors.append(
                    f"{blocker.card.name} cannot block due to {source_name}"
                )

    # Check for inherent "cannot block" in oracle text
    if _has_cannot_block(blocker):
        errors.append(f"{blocker.card.name} has an inherent cannot-block restriction")

    # Check for "cannot block" keyword
    keywords = blocker.card.keywords or []
    for kw in keywords:
        kw_lower = kw.lower()
        if "cannot block" in kw_lower or "can't block" in kw_lower:
            errors.append(f"{blocker.card.name} has the '{kw}' restriction")

    return errors


def check_unblockable(
    game_state: GameState,
    attacker: Permanent,
) -> list[str]:
    """
    Check if an attacker cannot be blocked.

    Args:
        game_state: Current game state.
        attacker: The attacking creature.

    Returns:
        List of error messages explaining why the attacker is unblockable.
    """
    errors: list[str] = []

    # Check for "can't be blocked" in oracle text
    if _is_unblockable(attacker):
        errors.append(f"{attacker.card.name} can't be blocked")

    # Check for unblockable keywords
    keywords = attacker.card.keywords or []
    for kw in keywords:
        kw_lower = kw.lower()
        if "can't be blocked" in kw_lower or "cannot be blocked" in kw_lower:
            errors.append(f"{attacker.card.name} has the '{kw}' unblockable ability")

    # Check block constraints for can_only_block restrictions that effectively
    # make this attacker unblockable
    for constraint in game_state.block_constraints:
        if constraint.constraint_type == "unblockable":
            if constraint.affected_id in (attacker.id, "all"):
                errors.append(
                    f"{attacker.card.name} is unblockable due to active constraint"
                )

    return errors


def check_can_only_block_restriction(
    game_state: GameState,
    blocker: Permanent,
    attacker: Permanent,
) -> list[str]:
    """
    Check if a blocker can only block certain types of creatures.

    CR 509: Some creatures can only block specific types.
    Examples: "Can only block flying creatures", "Can only block creatures
    with flying or reach".

    Args:
        game_state: Current game state.
        blocker: The creature attempting to block.
        attacker: The attacking creature being blocked.

    Returns:
        List of error messages if the blocker cannot block this attacker.
    """
    errors: list[str] = []

    # Parse "can only block" restrictions from blocker
    restrictions = _parse_can_only_block(blocker)
    for restriction in restrictions:
        restriction_type = restriction.get("type", "")
        restriction_value = restriction.get("value", "")

        if restriction_type == "keyword":
            # "Can only block creatures with <keyword>"
            attacker_keywords = attacker.card.keywords or []
            if restriction_value.lower() not in [k.lower() for k in attacker_keywords]:
                errors.append(
                    f"{blocker.card.name} can only block creatures with "
                    f"{restriction_value}, but {attacker.card.name} does not have it"
                )

        elif restriction_type == "flying":
            # "Can only block flying creatures"
            if "flying" not in [k.lower() for k in (attacker.card.keywords or [])]:
                errors.append(
                    f"{blocker.card.name} can only block flying creatures, "
                    f"but {attacker.card.name} does not have flying"
                )

        elif restriction_type == "legendary":
            # "Can only block legendary creatures"
            if "legendary" not in attacker.card.type_line.lower():
                errors.append(
                    f"{blocker.card.name} can only block legendary creatures, "
                    f"but {attacker.card.name} is not legendary"
                )

        elif restriction_type == "snow":
            # "Can only block snow creatures"
            if "snow" not in (attacker.card.supertypes or []):
                errors.append(
                    f"{blocker.card.name} can only block snow creatures, "
                    f"but {attacker.card.name} is not a snow creature"
                )

        elif restriction_type == "type":
            # "Can only block <type> creatures" (e.g., "Elf", "Human")
            if restriction_value.lower() not in attacker.card.type_line.lower():
                errors.append(
                    f"{blocker.card.name} can only block {restriction_value} creatures, "
                    f"but {attacker.card.name} is not a {restriction_value}"
                )

    # Check block constraints for can_only_block restrictions
    for constraint in game_state.block_constraints:
        if constraint.constraint_type == "can_only_block_flyers":
            if constraint.affected_id in (blocker.id, "all"):
                attacker_keywords = attacker.card.keywords or []
                if "flying" not in [k.lower() for k in attacker_keywords]:
                    errors.append(
                        f"{blocker.card.name} can only block flying creatures "
                        f"due to active constraint"
                    )

        elif constraint.constraint_type == "min_power_to_block":
            if constraint.affected_id in (blocker.id, "all"):
                min_power = int(constraint.restriction or "0")
                attacker_power = _get_power(attacker)
                if attacker_power < min_power:
                    errors.append(
                        f"{blocker.card.name} can only block creatures with power "
                        f"{min_power} or greater, but {attacker.card.name} has power {attacker_power}"
                    )

    return errors


def parse_blocking_restrictions(oracle_text: str) -> list[dict]:
    """
    Parse blocking restriction patterns from oracle text.

    Args:
        oracle_text: Card's oracle text.

    Returns:
        List of restriction dicts with 'type' and 'details'.
    """
    restrictions: list[dict] = []

    for pattern in _CANNOT_BLOCK_PATTERNS:
        match = pattern.search(oracle_text)
        if match:
            restrictions.append({
                "type": "cannot_block",
                "pattern": pattern.pattern,
            })

    for pattern in _CAN_ONLY_BLOCK_PATTERNS:
        match = pattern.search(oracle_text)
        if match:
            restrictions.append({
                "type": "can_only_block",
                "pattern": pattern.pattern,
                "groups": match.groups(),
            })

    for pattern in _UNBLOCKABLE_PATTERNS:
        match = pattern.search(oracle_text)
        if match:
            restrictions.append({
                "type": "unblockable",
                "pattern": pattern.pattern,
            })

    return restrictions


def create_cannot_block_constraint(
    source_perm: Permanent,
    affected_id: str = "all",
) -> "BlockConstraint":
    """
    Create a BlockConstraint for a cannot-block effect.

    Args:
        source_perm: The permanent creating the constraint.
        affected_id: Permanent ID or "all" for all creatures.

    Returns:
        BlockConstraint ready to add to game_state.block_constraints.
    """
    from mtg_engine.models.game import BlockConstraint

    return BlockConstraint(
        source_id=source_perm.id,
        affected_id=affected_id,
        constraint_type="cannot_block",
    )


def create_unblockable_constraint(
    source_perm: Permanent,
    affected_id: str = "all",
) -> "BlockConstraint":
    """
    Create a BlockConstraint for an unblockable effect.

    Args:
        source_perm: The permanent creating the constraint.
        affected_id: Permanent ID or "all" for all creatures.

    Returns:
        BlockConstraint ready to add to game_state.block_constraints.
    """
    from mtg_engine.models.game import BlockConstraint

    return BlockConstraint(
        source_id=source_perm.id,
        affected_id=affected_id,
        constraint_type="unblockable",
    )


def create_can_only_block_flyers_constraint(
    source_perm: Permanent,
    affected_id: str = "all",
) -> "BlockConstraint":
    """
    Create a BlockConstraint for a can-only-block-flyers effect.

    Args:
        source_perm: The permanent creating the constraint.
        affected_id: Permanent ID or "all" for all creatures.

    Returns:
        BlockConstraint ready to add to game_state.block_constraints.
    """
    from mtg_engine.models.game import BlockConstraint

    return BlockConstraint(
        source_id=source_perm.id,
        affected_id=affected_id,
        constraint_type="can_only_block_flyers",
    )


# ─── Private helpers ──────────────────────────────────────────────────────────


def _has_cannot_block(perm: Permanent) -> bool:
    """Check if a permanent has a cannot-block restriction in oracle text."""
    oracle = perm.card.oracle_text or ""
    return any(p.search(oracle) for p in _CANNOT_BLOCK_PATTERNS)


def _is_unblockable(perm: Permanent) -> bool:
    """Check if a permanent has an unblockable ability in oracle text."""
    oracle = perm.card.oracle_text or ""
    return any(p.search(oracle) for p in _UNBLOCKABLE_PATTERNS)


def _parse_can_only_block(perm: Permanent) -> list[dict]:
    """Parse 'can only block' restrictions from a permanent's oracle text."""
    oracle = perm.card.oracle_text or ""
    restrictions: list[dict] = []

    for pattern in _CAN_ONLY_BLOCK_PATTERNS:
        match = pattern.search(oracle)
        if match:
            groups = match.groups()
            if groups:
                value = groups[0].lower()
                # Determine restriction type
                if value in ("flying", "legendary", "snow"):
                    restrictions.append({
                        "type": value,
                        "value": value,
                    })
                elif value in ("reach", "first strike", "double strike",
                               "trample", "haste", "deathtouch", "lifelink",
                               "indestructible", "hexproof", "shroud", "ward"):
                    restrictions.append({
                        "type": "keyword",
                        "value": value,
                    })
                else:
                    restrictions.append({
                        "type": "type",
                        "value": value,
                    })

    return restrictions


def _get_power(perm: Permanent) -> int:
    """Get effective power of a permanent."""
    try:
        p = int(perm.card.power or "0")
    except (ValueError, TypeError):
        p = 0
    p += perm.counters.get("+1/+1", 0) - perm.counters.get("-1/-1", 0)
    p += perm.power_bonus
    return max(0, p)
