"""
Combat system package.

Combines the original combat module with Phase 500 enhancements:
attack requirements, blocking restrictions, banding, flanking,
and multi-block restrictions.
"""
# Re-export original combat module functions
from mtg_engine.engine.combat.core import (
    declare_attackers,
    declare_blockers,
    order_blockers,
    assign_combat_damage,
    end_combat,
    has_first_strike_combatants,
    _get_perm,
    _is_creature,
    _has_keyword,
    _effective_power,
    _effective_toughness,
    _is_lethal_damage,
    _has_hexproof_or_shroud,
    _has_protection,
    _has_protection_from,
    _get_protection_qualities,
    _get_defending_player_name,
    _is_planeswalker_by_id,
    _get_source_qualities,
    _LANDWALK_MAP,
    _check_landwalk,
    _validate_damage_assignments,
    _auto_assign_damage,
    _generate_blocker_damage,
)

__all__ = [
    "declare_attackers",
    "declare_blockers",
    "order_blockers",
    "assign_combat_damage",
    "end_combat",
    "has_first_strike_combatants",
    "_get_perm",
    "_is_creature",
    "_has_keyword",
    "_effective_power",
    "_effective_toughness",
    "_is_lethal_damage",
    "_has_hexproof_or_shroud",
    "_has_protection",
    "_has_protection_from",
    "_get_protection_qualities",
    "_get_defending_player_name",
    "_is_planeswalker_by_id",
    "_get_source_qualities",
    "_LANDWALK_MAP",
    "_check_landwalk",
    "_validate_damage_assignments",
    "_auto_assign_damage",
    "_generate_blocker_damage",
]
