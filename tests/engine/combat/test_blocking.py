"""Tests for blocking restrictions (CMB-02, CMB-05)."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.engine.combat.blocking import (
    check_cannot_block,
    check_unblockable,
    check_can_only_block_restriction,
    parse_blocking_restrictions,
    create_cannot_block_constraint,
    create_unblockable_constraint,
    create_can_only_block_flyers_constraint,
)
from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, Permanent, BlockConstraint,
)


def _make_game_with_creatures(
    creatures: list[dict] | None = None,
    block_constraints: list[BlockConstraint] | None = None,
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
            colors=c.get("colors", []),
            supertypes=c.get("supertypes", []),
        )
        perm = Permanent(
            card=card,
            controller=c.get("controller", "p1"),
            tapped=c.get("tapped", False),
        )
        perms.append(perm)

    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.COMBAT, step=Step.DECLARE_BLOCKERS,
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
        battlefield=perms,
        block_constraints=block_constraints or [],
    )
    return gs, perms


def test_cannot_block_constraint():
    """Cannot-block constraint prevents blocking."""
    gs, perms = _make_game_with_creatures([
        {"name": "Propaganda", "type_line": "Enchantment", "controller": "p2"},
        {"name": "Creature A", "controller": "p1"},
    ])

    constraint = create_cannot_block_constraint(perms[0], affected_id="all")
    gs.block_constraints.append(constraint)

    errors = check_cannot_block(gs, perms[1])
    assert len(errors) == 1
    assert "cannot block" in errors[0]


def test_cannot_block_specific():
    """Cannot-block constraint for specific creature."""
    gs, perms = _make_game_with_creatures([
        {"name": "Propaganda", "type_line": "Enchantment", "controller": "p2"},
        {"name": "Creature A", "controller": "p1"},
        {"name": "Creature B", "controller": "p1"},
    ])

    constraint = create_cannot_block_constraint(perms[0], affected_id=perms[1].id)
    gs.block_constraints.append(constraint)

    errors_a = check_cannot_block(gs, perms[1])
    assert len(errors_a) == 1

    errors_b = check_cannot_block(gs, perms[2])
    assert len(errors_b) == 0


def test_cannot_block_inherent():
    """Inherent cannot-block from oracle text."""
    gs, perms = _make_game_with_creatures([
        {"name": "Creature A", "controller": "p1",
         "oracle_text": "This creature cannot block."},
    ])

    errors = check_cannot_block(gs, perms[0])
    assert len(errors) == 1
    assert "cannot-block" in errors[0]


def test_cannot_block_keyword():
    """Cannot-block from keyword list."""
    gs, perms = _make_game_with_creatures([
        {"name": "Creature A", "controller": "p1",
         "keywords": ["cannot block"]},
    ])

    errors = check_cannot_block(gs, perms[0])
    assert len(errors) == 1


def test_no_cannot_block():
    """Normal creature has no blocking restrictions."""
    gs, perms = _make_game_with_creatures([
        {"name": "Creature A", "controller": "p1"},
    ])

    errors = check_cannot_block(gs, perms[0])
    assert len(errors) == 0


def test_unblockable_oracle():
    """Unblockable from oracle text."""
    gs, perms = _make_game_with_creatures([
        {"name": "Unblockable", "controller": "p2",
         "oracle_text": "This creature can't be blocked."},
    ])

    errors = check_unblockable(gs, perms[0])
    assert len(errors) == 1
    assert "can't be blocked" in errors[0]


def test_unblockable_constraint():
    """Unblockable from constraint."""
    gs, perms = _make_game_with_creatures([
        {"name": "Haste Enchantment", "type_line": "Enchantment", "controller": "p2"},
        {"name": "Creature A", "controller": "p2"},
    ])

    constraint = create_unblockable_constraint(perms[0], affected_id=perms[1].id)
    gs.block_constraints.append(constraint)

    errors = check_unblockable(gs, perms[1])
    assert len(errors) == 1


def test_can_only_block_flying():
    """Creature can only block flying creatures."""
    gs, perms = _make_game_with_creatures([
        {"name": "Sky Blocker", "controller": "p1",
         "oracle_text": "This creature can only block flying creatures."},
        {"name": "Normal Attacker", "controller": "p2",
         "keywords": []},
        {"name": "Flying Attacker", "controller": "p2",
         "keywords": ["flying"]},
    ])

    # Cannot block non-flying
    errors = check_can_only_block_restriction(gs, perms[0], perms[1])
    assert len(errors) == 1
    assert "flying" in errors[0]

    # Can block flying
    errors = check_can_only_block_restriction(gs, perms[0], perms[2])
    assert len(errors) == 0


def test_can_only_block_flyers_constraint():
    """Can-only-block-flyers constraint."""
    gs, perms = _make_game_with_creatures([
        {"name": "Enchantment", "type_line": "Enchantment", "controller": "p2"},
        {"name": "Blocker", "controller": "p1"},
        {"name": "Normal Attacker", "controller": "p2"},
    ])

    constraint = create_can_only_block_flyers_constraint(perms[0], affected_id=perms[1].id)
    gs.block_constraints.append(constraint)

    errors = check_can_only_block_restriction(gs, perms[1], perms[2])
    assert len(errors) == 1
    assert "flying" in errors[0]


def test_can_only_block_keyword():
    """Creature can only block creatures with a specific keyword."""
    gs, perms = _make_game_with_creatures([
        {"name": "Special Blocker", "controller": "p1",
         "oracle_text": "This creature can only block creatures with flying."},
        {"name": "Normal Attacker", "controller": "p2",
         "keywords": ["trample"]},
        {"name": "Flying Attacker", "controller": "p2",
         "keywords": ["flying"]},
    ])

    errors = check_can_only_block_restriction(gs, perms[0], perms[1])
    assert len(errors) == 1

    errors = check_can_only_block_restriction(gs, perms[0], perms[2])
    assert len(errors) == 0


def test_can_only_block_legendary():
    """Creature can only block legendary creatures."""
    gs, perms = _make_game_with_creatures([
        {"name": "Legendary Blocker", "controller": "p1",
         "oracle_text": "This creature can only block legendary creatures."},
        {"name": "Normal Attacker", "type_line": "Creature — Human", "controller": "p2"},
        {"name": "Legendary Attacker", "type_line": "Legendary Creature — Human", "controller": "p2"},
    ])

    errors = check_can_only_block_restriction(gs, perms[0], perms[1])
    assert len(errors) == 1
    assert "legendary" in errors[0]

    errors = check_can_only_block_restriction(gs, perms[0], perms[2])
    assert len(errors) == 0


def test_can_only_block_snow():
    """Creature can only block snow creatures."""
    gs, perms = _make_game_with_creatures([
        {"name": "Snow Blocker", "controller": "p1",
         "oracle_text": "This creature can only block snow creatures."},
        {"name": "Normal Attacker", "type_line": "Creature — Human",
         "controller": "p2", "supertypes": []},
        {"name": "Snow Attacker", "type_line": "Snow Creature — Human",
         "controller": "p2", "supertypes": ["snow"]},
    ])

    errors = check_can_only_block_restriction(gs, perms[0], perms[1])
    assert len(errors) == 1

    errors = check_can_only_block_restriction(gs, perms[0], perms[2])
    assert len(errors) == 0


def test_parse_cannot_block():
    """Parse cannot-block patterns."""
    restrictions = parse_blocking_restrictions("This creature cannot block.")
    assert len(restrictions) >= 1
    assert any(r["type"] == "cannot_block" for r in restrictions)


def test_parse_unblockable():
    """Parse unblockable patterns."""
    restrictions = parse_blocking_restrictions("This creature can't be blocked.")
    assert len(restrictions) >= 1
    assert any(r["type"] == "unblockable" for r in restrictions)


def test_parse_can_only_block():
    """Parse can-only-block patterns."""
    restrictions = parse_blocking_restrictions("This creature can only block flying creatures.")
    assert len(restrictions) >= 1
    assert any(r["type"] == "can_only_block" for r in restrictions)


def test_parse_no_restrictions():
    """No restrictions parsed from normal text."""
    restrictions = parse_blocking_restrictions("Flying. Trample.")
    assert len(restrictions) == 0


def test_create_cannot_block_constraint():
    """Create cannot-block constraint."""
    card = Card(name="Propaganda", type_line="Enchantment")
    perm = Permanent(card=card, controller="p1")
    constraint = create_cannot_block_constraint(perm, affected_id="all")

    assert constraint.constraint_type == "cannot_block"
    assert constraint.affected_id == "all"


def test_create_unblockable_constraint():
    """Create unblockable constraint."""
    card = Card(name="Haste Aura", type_line="Enchantment")
    perm = Permanent(card=card, controller="p1")
    constraint = create_unblockable_constraint(perm, affected_id="all")

    assert constraint.constraint_type == "unblockable"


def test_create_can_only_block_flyers_constraint():
    """Create can-only-block-flyers constraint."""
    card = Card(name="Sky Restriction", type_line="Enchantment")
    perm = Permanent(card=card, controller="p1")
    constraint = create_can_only_block_flyers_constraint(perm, affected_id="all")

    assert constraint.constraint_type == "can_only_block_flyers"
