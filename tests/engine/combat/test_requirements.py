"""Tests for attack requirements (CMB-01)."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.engine.combat.requirements import (
    check_must_attack_requirements,
    check_cannot_attack_restrictions,
    check_cannot_attack_alone,
    parse_attack_requirements,
    create_must_attack_constraint,
    create_cannot_attack_constraint,
)
from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, Permanent, AttackConstraint,
)


def _make_game_with_creatures(
    creatures: list[dict] | None = None,
    attack_constraints: list[AttackConstraint] | None = None,
) -> tuple[GameState, list[Permanent]]:
    """Create a game with creatures on the battlefield."""
    if creatures is None:
        creatures = []

    perms: list[Permanent] = []
    for c in creatures:
        card = Card(
            name=c.get("name", "Creature"),
            type_line=c.get("type_line", "Creature — Human"),
            keywords=c.get("keywords", []),
            oracle_text=c.get("oracle_text", ""),
            power=c.get("power", "2"),
            toughness=c.get("toughness", "2"),
        )
        perm = Permanent(
            card=card,
            controller=c.get("controller", "p1"),
            tapped=c.get("tapped", False),
            summoning_sick=c.get("summoning_sick", False),
        )
        perms.append(perm)

    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS,
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
        battlefield=perms,
        attack_constraints=attack_constraints or [],
    )
    return gs, perms


def test_must_attack_all_constraint():
    """Creatures must attack when all-creatures must-attack constraint is active."""
    gs, perms = _make_game_with_creatures([
        {"name": "Creature A", "controller": "p1"},
        {"name": "Creature B", "controller": "p1"},
    ])

    # Add must-attack constraint from Creature A affecting all
    constraint = create_must_attack_constraint(perms[0], affected_id="all")
    gs.attack_constraints.append(constraint)

    # Only Creature A attacks, Creature B should be flagged
    errors = check_must_attack_requirements(gs, [perms[0].id])
    assert len(errors) == 1
    assert "Creature B" in errors[0]
    assert "must attack" in errors[0]


def test_must_attack_specific_constraint():
    """Specific creature must attack when constrained."""
    gs, perms = _make_game_with_creatures([
        {"name": "Creature A", "controller": "p1"},
        {"name": "Creature B", "controller": "p1"},
    ])

    # Creature B must attack
    constraint = create_must_attack_constraint(perms[0], affected_id=perms[1].id)
    gs.attack_constraints.append(constraint)

    errors = check_must_attack_requirements(gs, [perms[0].id])
    assert len(errors) == 1
    assert "Creature B" in errors[0]


def test_must_attack_all_declared():
    """No errors when all required creatures are declared."""
    gs, perms = _make_game_with_creatures([
        {"name": "Creature A", "controller": "p1"},
        {"name": "Creature B", "controller": "p1"},
    ])

    constraint = create_must_attack_constraint(perms[0], affected_id="all")
    gs.attack_constraints.append(constraint)

    errors = check_must_attack_requirements(gs, [perms[0].id, perms[1].id])
    assert len(errors) == 0


def test_must_attack_summoning_sick_exempt():
    """Summoning-sick creatures are exempt from must-attack (can't attack)."""
    gs, perms = _make_game_with_creatures([
        {"name": "Creature A", "controller": "p1", "summoning_sick": False},
        {"name": "Creature B", "controller": "p1", "summoning_sick": True},
    ])

    constraint = create_must_attack_constraint(perms[0], affected_id="all")
    gs.attack_constraints.append(constraint)

    errors = check_must_attack_requirements(gs, [perms[0].id])
    assert len(errors) == 0


def test_cannot_attack_constraint():
    """Cannot-attack constraint prevents attacking."""
    gs, perms = _make_game_with_creatures([
        {"name": "Creature A", "controller": "p1"},
    ])

    constraint = create_cannot_attack_constraint(perms[0], affected_id=perms[0].id)
    gs.attack_constraints.append(constraint)

    errors = check_cannot_attack_restrictions(gs, perms[0])
    assert len(errors) == 1
    assert "cannot attack" in errors[0]


def test_cannot_attack_defender():
    """Defender keyword prevents attacking."""
    gs, perms = _make_game_with_creatures([
        {"name": "Wall", "type_line": "Creature — Wall", "keywords": ["defender"]},
    ])

    errors = check_cannot_attack_restrictions(gs, perms[0])
    assert len(errors) == 1
    assert "defender" in errors[0]


def test_attacks_alone_violation():
    """Attacks alone creature cannot attack with others."""
    gs, perms = _make_game_with_creatures([
        {"name": "Raid Boss", "controller": "p1", "oracle_text": "This creature attacks alone."},
        {"name": "Minion", "controller": "p1"},
    ])

    errors = check_must_attack_requirements(gs, [perms[0].id, perms[1].id])
    assert len(errors) == 1
    assert "attacks alone" in errors[0]


def test_attacks_alone_ok():
    """Attacks alone creature can attack by itself."""
    gs, perms = _make_game_with_creatures([
        {"name": "Raid Boss", "controller": "p1", "oracle_text": "This creature attacks alone."},
    ])

    errors = check_must_attack_requirements(gs, [perms[0].id])
    assert len(errors) == 0


def test_cannot_attack_alone():
    """Creature that cannot attack alone is flagged when attacking solo."""
    gs, perms = _make_game_with_creatures([
        {"name": "Minion", "controller": "p1"},
    ])

    assert check_cannot_attack_alone(gs, perms[0], [perms[0].id]) is False

    # With "cannot attack alone" oracle text
    perms[0].card.oracle_text = "This creature cannot attack alone."
    assert check_cannot_attack_alone(gs, perms[0], [perms[0].id]) is True


def test_cannot_attack_alone_with_partner():
    """Creature that cannot attack alone is fine with another attacker."""
    gs, perms = _make_game_with_creatures([
        {"name": "Minion A", "controller": "p1", "oracle_text": "This creature cannot attack alone."},
        {"name": "Minion B", "controller": "p1"},
    ])

    assert check_cannot_attack_alone(gs, perms[0], [perms[0].id, perms[1].id]) is False


def test_parse_must_attack():
    """Parse must-attack patterns from oracle text."""
    reqs = parse_attack_requirements("Creatures you control must attack if able.")
    assert len(reqs) >= 1
    assert any(r["type"] == "must_attack" for r in reqs)


def test_parse_attacks_alone():
    """Parse attacks alone pattern from oracle text."""
    reqs = parse_attack_requirements("This creature attacks alone.")
    assert len(reqs) >= 1
    assert any(r["type"] == "attacks_alone" for r in reqs)


def test_parse_cannot_attack_alone():
    """Parse cannot attack alone pattern from oracle text."""
    reqs = parse_attack_requirements("This creature cannot attack alone.")
    assert len(reqs) >= 1
    assert any(r["type"] == "cannot_attack_alone" for r in reqs)


def test_parse_no_requirements():
    """No requirements parsed from normal oracle text."""
    reqs = parse_attack_requirements("Flying. Trample.")
    assert len(reqs) == 0


def test_create_must_attack_constraint():
    """Create must-attack constraint."""
    card = Card(name="Propaganda", type_line="Enchantment")
    perm = Permanent(card=card, controller="p1")
    constraint = create_must_attack_constraint(perm, affected_id="all")

    assert constraint.constraint_type == "must_attack"
    assert constraint.affected_id == "all"
    assert constraint.source_id == perm.id


def test_create_cannot_attack_constraint():
    """Create cannot-attack constraint."""
    card = Card(name="Cowards", type_line="Enchantment")
    perm = Permanent(card=card, controller="p1")
    constraint = create_cannot_attack_constraint(perm, affected_id="all")

    assert constraint.constraint_type == "cannot_attack"
    assert constraint.affected_id == "all"
