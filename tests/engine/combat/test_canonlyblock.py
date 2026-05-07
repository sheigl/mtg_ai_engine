"""Tests for multi-block restrictions (CMB-05)."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.engine.combat.blocking import (
    check_can_only_block_restriction,
    parse_blocking_restrictions,
    create_can_only_block_flyers_constraint,
)
from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, Permanent, BlockConstraint,
)


def _make_perm(
    name: str = "Creature",
    type_line: str = "Creature — Human",
    keywords: list[str] | None = None,
    oracle_text: str = "",
    controller: str = "p1",
    power: str = "2",
    toughness: str = "2",
    colors: list[str] | None = None,
    supertypes: list[str] | None = None,
) -> Permanent:
    """Create a permanent with given properties."""
    card = Card(
        name=name,
        type_line=type_line,
        keywords=keywords or [],
        oracle_text=oracle_text,
        power=power,
        toughness=toughness,
        colors=colors or [],
        supertypes=supertypes or [],
    )
    return Permanent(card=card, controller=controller)


def _make_game(perms: list[Permanent], block_constraints: list[BlockConstraint] | None = None) -> GameState:
    """Create a game state with given permanents."""
    return GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.COMBAT, step=Step.DECLARE_BLOCKERS,
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
        battlefield=perms,
        block_constraints=block_constraints or [],
    )


def test_can_only_block_flying_oracle():
    """Creature with 'can only block flying' from oracle text."""
    blocker = _make_perm(
        name="Sky Guardian",
        oracle_text="This creature can only block flying creatures.",
        controller="p1",
    )
    normal_attacker = _make_perm(name="Bear", controller="p2", keywords=[])
    flying_attacker = _make_perm(name="Bird", controller="p2", keywords=["flying"])

    gs = _make_game([blocker, normal_attacker, flying_attacker])

    errors = check_can_only_block_restriction(gs, blocker, normal_attacker)
    assert len(errors) == 1

    errors = check_can_only_block_restriction(gs, blocker, flying_attacker)
    assert len(errors) == 0


def test_can_only_block_multiple_keywords():
    """Creature can only block creatures with specific keywords."""
    blocker = _make_perm(
        name="Reach Blocker",
        oracle_text="This creature can only block creatures with reach.",
        controller="p1",
    )
    no_reach = _make_perm(name="Normal", controller="p2", keywords=["flying"])
    has_reach = _make_perm(name="Reach Creature", controller="p2", keywords=["flying", "reach"])

    gs = _make_game([blocker, no_reach, has_reach])

    errors = check_can_only_block_restriction(gs, blocker, no_reach)
    assert len(errors) == 1
    assert "reach" in errors[0]

    errors = check_can_only_block_restriction(gs, blocker, has_reach)
    assert len(errors) == 0


def test_can_only_block_type():
    """Creature can only block a specific creature type."""
    blocker = _make_perm(
        name="Elf Hunter",
        oracle_text="This creature can only block Elf creatures.",
        controller="p1",
    )
    human = _make_perm(name="Human", type_line="Creature — Human", controller="p2")
    elf = _make_perm(name="Elf", type_line="Creature — Elf", controller="p2")

    gs = _make_game([blocker, human, elf])

    errors = check_can_only_block_restriction(gs, blocker, human)
    assert len(errors) == 1
    assert "Elf" in errors[0]

    errors = check_can_only_block_restriction(gs, blocker, elf)
    assert len(errors) == 0


def test_parse_can_only_block_flying():
    """Parse 'can only block flying creatures' pattern."""
    restrictions = parse_blocking_restrictions("This creature can only block flying creatures.")
    assert len(restrictions) >= 1
    assert any(r["type"] == "can_only_block" for r in restrictions)


def test_parse_can_only_block_keyword():
    """Parse 'can only block creatures with <keyword>' pattern."""
    restrictions = parse_blocking_restrictions(
        "This creature can only block creatures with flying."
    )
    assert len(restrictions) >= 1


def test_constraint_can_only_block_flyers():
    """Can-only-block-flyers constraint from enchantment."""
    blocker = _make_perm(name="Blocker", controller="p1")
    normal = _make_perm(name="Normal", controller="p2", keywords=[])
    flying = _make_perm(name="Flying", controller="p2", keywords=["flying"])

    constraint = create_can_only_block_flyers_constraint(
        _make_perm(name="Enchantment", type_line="Enchantment", controller="p2"),
        affected_id=blocker.id,
    )
    gs = _make_game([blocker, normal, flying], [constraint])

    errors = check_can_only_block_restriction(gs, blocker, normal)
    assert len(errors) == 1

    errors = check_can_only_block_restriction(gs, blocker, flying)
    assert len(errors) == 0


def test_constraint_affects_all():
    """Can-only-block-flyers constraint affects all creatures."""
    blocker1 = _make_perm(name="Blocker 1", controller="p1")
    blocker2 = _make_perm(name="Blocker 2", controller="p1")
    normal = _make_perm(name="Normal", controller="p2", keywords=[])

    constraint = create_can_only_block_flyers_constraint(
        _make_perm(name="Enchantment", type_line="Enchantment", controller="p2"),
        affected_id="all",
    )
    gs = _make_game([blocker1, blocker2, normal], [constraint])

    errors1 = check_can_only_block_restriction(gs, blocker1, normal)
    assert len(errors1) == 1

    errors2 = check_can_only_block_restriction(gs, blocker2, normal)
    assert len(errors2) == 1
