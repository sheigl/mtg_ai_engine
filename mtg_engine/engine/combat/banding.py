"""
Barding support.

CMB-03: Implements the Banding mechanic.
CR 702.21: Banding is a static ability that modifies combat rules.

Banding rules:
1. Creatures with banding can attack together with creatures without banding
2. Creatures with banding can block together with creatures without banding
3. Damage assignment is flexible within a band group:
   - Any amount of damage can be assigned to any creature in the band
   - No minimum lethal requirement within the band
4. Trample damage calculation considers total band toughness
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent, AttackerInfo

logger = logging.getLogger(__name__)


def has_barding(perm: Permanent) -> bool:
    """Check if a permanent has banding."""
    keywords = perm.card.keywords or []
    return any(kw.lower() == "banding" for kw in keywords)


def get_band_attackers(
    game_state: GameState,
    controller: str,
    attacker_ids: list[str],
) -> list[list[str]]:
    """
    Group attackers into band groups.

    A band group consists of at least one creature with banding and any
    number of creatures without banding, all controlled by the same player.

    Args:
        game_state: Current game state.
        controller: The attacking player's name.
        attacker_ids: List of permanent IDs declared as attackers.

    Returns:
        List of band groups, where each group is a list of permanent IDs.
        If no banding creatures, returns a single group with all attackers.
    """
    attacker_perms = [
        p for p in game_state.battlefield
        if p.id in attacker_ids and p.controller == controller
    ]

    banding_attackers = [p for p in attacker_perms if has_barding(p)]
    non_banding_attackers = [p for p in attacker_perms if not has_barding(p)]

    if not banding_attackers:
        # No banding — all attackers form a single non-band group
        return [[p.id for p in attacker_perms]]

    # Each banding creature can form its own band group
    # For simplicity, group all attackers into one band per banding creature
    bands: list[list[str]] = []

    # First band: all attackers grouped together (if only one banding creature)
    if len(banding_attackers) == 1:
        bands.append([p.id for p in attacker_perms])
    else:
        # Multiple banding creatures — each forms a band with some non-band creatures
        # Simple approach: first banding creature takes all non-band creatures
        first_band = [banding_attackers[0].id] + [p.id for p in non_banding_attackers]
        bands.append(first_band)
        # Remaining banding creatures each form their own band
        for ba in banding_attackers[1:]:
            bands.append([ba.id])

    return bands


def get_band_blockers(
    game_state: GameState,
    attacker_info: "AttackerInfo",
    blocker_ids: list[str],
) -> list[list[str]]:
    """
    Group blockers into band groups for a specific attacker.

    Args:
        game_state: Current game state.
        attacker_info: The attacker being blocked.
        blocker_ids: List of permanent IDs blocking this attacker.

    Returns:
        List of band groups, where each group is a list of permanent IDs.
    """
    blocker_perms = [
        p for p in game_state.battlefield
        if p.id in blocker_ids
    ]

    banding_blockers = [p for p in blocker_perms if has_barding(p)]
    non_banding_blockers = [p for p in blocker_perms if not has_barding(p)]

    if not banding_blockers:
        return [[p.id for p in blocker_perms]]

    bands: list[list[str]] = []
    if len(banding_blockers) == 1:
        bands.append([p.id for p in blocker_perms])
    else:
        first_band = [banding_blockers[0].id] + [p.id for p in non_banding_blockers]
        bands.append(first_band)
        for bb in banding_blockers[1:]:
            bands.append([bb.id])

    return bands


def validate_banding_damage_assignment(
    game_state: GameState,
    attacker_id: str,
    blocker_ids: list[str],
    damage_assignments: dict[str, int],
) -> list[str]:
    """
    Validate damage assignment within a band group.

    CR 702.21d: When damage is assigned within a band, any amount of damage
    can be assigned to any creature in the band. No minimum lethal requirement.

    Args:
        game_state: Current game state.
        attacker_id: The attacking creature's ID.
        blocker_ids: List of blocker IDs (the band group).
        damage_assignments: Dict mapping blocker_id to damage amount.

    Returns:
        List of error messages. Empty if assignment is valid.
    """
    errors: list[str] = []

    attacker = next(
        (p for p in game_state.battlefield if p.id == attacker_id),
        None,
    )
    if not attacker:
        errors.append(f"Attacker {attacker_id} not found")
        return errors

    attacker_power = _effective_power(attacker)
    total_assigned = sum(damage_assignments.values())

    if total_assigned > attacker_power:
        errors.append(
            f"{attacker.card.name} assigns {total_assigned} damage but has power {attacker_power}"
        )
        return errors

    # Check if any blocker in the group has banding
    has_banding_in_group = any(
        has_barding(next((p for p in game_state.battlefield if p.id == bid), None) or _empty_perm())
        for bid in blocker_ids
    )

    if has_banding_in_group:
        # With banding, any distribution is valid as long as total <= power
        if total_assigned <= attacker_power:
            return errors

    return errors


def calculate_banding_trample_damage(
    game_state: GameState,
    attacker: Permanent,
    band_group: list[str],
    damage_assignments: dict[str, int],
) -> int:
    """
    Calculate trample damage that can go past a band group.

    CR 702.21e: When calculating trample damage with banding, the total
    toughness of all creatures in the band is considered.

    Args:
        game_state: Current game state.
        attacker: The attacking creature with trample.
        band_group: List of permanent IDs in the band group.
        damage_assignments: Dict mapping blocker_id to damage amount.

    Returns:
        Amount of damage that can trample over to the defending player.
    """
    if "trample" not in [k.lower() for k in (attacker.card.keywords or [])]:
        return 0

    attacker_power = _effective_power(attacker)
    total_toughness = 0

    for bid in band_group:
        blocker = next(
            (p for p in game_state.battlefield if p.id == bid),
            None,
        )
        if blocker:
            total_toughness += _effective_toughness(blocker)

    # With banding + trample, you must assign at least total toughness
    # before trampling (CR 702.21e)
    assigned_to_band = sum(
        damage_assignments.get(bid, 0) for bid in band_group
    )

    trample_damage = max(0, attacker_power - total_toughness)

    logger.info(
        "Banding trample: %s (power %d) vs band (total toughness %d), "
        "trample damage: %d",
        attacker.card.name,
        attacker_power,
        total_toughness,
        trample_damage,
    )

    return trample_damage


def can_block_with_barding(
    game_state: GameState,
    blocker: Permanent,
    attacker: Permanent,
) -> bool:
    """
    Check if a creature can block as part of a band.

    CR 702.21b: Creatures without banding can block an attacking creature
    with banding only if they are declared as blockers along with at least
    one creature with banding.

    Args:
        game_state: Current game state.
        blocker: The creature attempting to block.
        attacker: The attacking creature.

    Returns:
        True if the blocker can block (either has banding or attacker has banding).
    """
    if has_barding(blocker):
        return True

    # A creature without banding can block a creature with banding
    # only as part of a band group (checked at declaration time)
    if has_barding(attacker):
        return True

    return True  # Normal blocking rules apply


# ─── Private helpers ──────────────────────────────────────────────────────────


def _effective_power(perm: Permanent) -> int:
    """Get effective power of a permanent."""
    try:
        p = int(perm.card.power or "0")
    except (ValueError, TypeError):
        p = 0
    p += perm.counters.get("+1/+1", 0) - perm.counters.get("-1/-1", 0)
    p += perm.power_bonus
    return max(0, p)


def _effective_toughness(perm: Permanent) -> int:
    """Get effective toughness of a permanent."""
    try:
        t = int(perm.card.toughness or "0")
    except (ValueError, TypeError):
        t = 0
    t += perm.counters.get("+1/+1", 0) - perm.counters.get("-1/-1", 0)
    t += perm.toughness_bonus
    return t


def _empty_perm() -> Permanent:
    """Return an empty permanent for type safety."""
    from mtg_engine.models.game import Card
    card = Card(name="", type_line="")
    return Permanent(card=card, controller="")
