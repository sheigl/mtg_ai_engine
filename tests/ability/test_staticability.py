"""Tests for static ability classes."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card
from mtg_engine.ability.staticability import (
    ContinuousPump, CantAttackBlock, HexproofGrant,
    IndestructibleGrant, create_static_ability,
)
from mtg_engine.engine.zones import put_permanent_onto_battlefield


def _make_test_game() -> GameState:
    """Create a basic test game."""
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    return GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
    )


def test_cant_attack_block_exists():
    """CantAttackBlock can be created."""
    ability = CantAttackBlock()
    assert ability is not None
    assert ability.restriction == "attack"


def test_continuous_pump_creation():
    """ContinuousPump can be created."""
    pump = ContinuousPump(power_bonus=2, toughness_bonus=2)
    assert pump.power_bonus == 2
    assert pump.toughness_bonus == 2


def test_continuous_pump_apply():
    """ContinuousPump applies to permanent."""
    gs = _make_test_game()
    
    bear = Card(
        name="Grizzly Bears",
        type_line="Creature — Bear",
        power="2",
        toughness="2",
    )
    
    gs, perm = put_permanent_onto_battlefield(gs, bear, "p1")
    
    assert perm.power_bonus == 0
    assert perm.toughness_bonus == 0
    
    pump = ContinuousPump(power_bonus=1, toughness_bonus=1)
    pump.apply(gs, perm)
    
    assert perm.power_bonus == 1
    assert perm.toughness_bonus == 1


def test_static_ability_registry():
    """Static ability registry works."""
    pump = create_static_ability("pump", power_bonus=1, toughness_bonus=1)
    assert isinstance(pump, ContinuousPump)
    
    cant = create_static_ability("cant_attack")
    assert isinstance(cant, CantAttackBlock)


def test_hexproof_grant():
    """HexproofGrant exists."""
    ability = HexproofGrant()
    assert ability is not None


def test_indestructible_grant():
    """IndestructibleGrant exists."""
    ability = IndestructibleGrant()
    assert ability is not None