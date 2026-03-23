"""
Combat constraint detection. US6 (014-rules-engine-completeness).
Scans battlefield oracle text to derive AttackConstraint and BlockConstraint entries.
CR 508 (declare attackers), CR 509 (declare blockers).
"""
import re
import logging

from mtg_engine.models.game import GameState, AttackConstraint, BlockConstraint

logger = logging.getLogger(__name__)

_ATTACK_COST_RE = re.compile(
    r"creatures? (?:can't|cannot) attack unless (?:their controller|you) pays? (\{[^}]+\})",
    re.IGNORECASE,
)
_CANT_BLOCK_RE = re.compile(
    r"\bcan't block\b",
    re.IGNORECASE,
)
_MUST_ATTACK_RE = re.compile(
    r"(?:attacks? each (?:combat|turn) if able|must attack)",
    re.IGNORECASE,
)


def derive_combat_constraints(
    game_state: GameState,
) -> tuple[list[AttackConstraint], list[BlockConstraint]]:
    """
    Scan all battlefield permanents and derive active attack/block constraints.
    Returns (attack_constraints, block_constraints).
    """
    attack_constraints: list[AttackConstraint] = []
    block_constraints: list[BlockConstraint] = []

    for perm in game_state.battlefield:
        oracle = (perm.card.oracle_text or "").strip()
        if not oracle:
            continue

        # Propaganda-style attack cost (global: affects all attackers)
        cost_match = _ATTACK_COST_RE.search(oracle)
        if cost_match:
            cost_str = cost_match.group(1)
            attack_constraints.append(AttackConstraint(
                source_id=perm.id,
                affected_id="all",
                constraint_type="cost_to_attack",
                cost=cost_str,
            ))
            logger.debug("Attack cost %s derived from %s", cost_str, perm.card.name)

        # Creature-level: "can't block" on this permanent itself
        if _CANT_BLOCK_RE.search(oracle):
            if "creature" in perm.card.type_line.lower():
                block_constraints.append(BlockConstraint(
                    source_id=perm.id,
                    affected_id=perm.id,
                    constraint_type="cannot_block",
                ))
                logger.debug("Cannot-block constraint derived from %s", perm.card.name)

        # Must-attack constraint on this permanent
        if _MUST_ATTACK_RE.search(oracle):
            if "creature" in perm.card.type_line.lower():
                attack_constraints.append(AttackConstraint(
                    source_id=perm.id,
                    affected_id=perm.id,
                    constraint_type="must_attack",
                ))
                logger.debug("Must-attack constraint derived from %s", perm.card.name)

        # Goad: creature with a goad counter must attack a player other than goad source controller
        for counter_key in perm.counters:
            if counter_key.startswith("goad_by_"):
                goad_controller = counter_key[len("goad_by_"):]
                attack_constraints.append(AttackConstraint(
                    source_id=perm.id,
                    affected_id=perm.id,
                    constraint_type="goad",
                    goad_controller=goad_controller,
                ))
                logger.debug(
                    "Goad constraint on %s (goad controller: %s)",
                    perm.card.name, goad_controller,
                )

    return attack_constraints, block_constraints
