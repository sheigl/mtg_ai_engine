import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.ability.cost import (
    CostType,
    ManaCost,
    TapCost,
    SacrificeCost,
    ExileCost,
    DiscardCost,
    LifeCost,
    LoyaltyCost,
    CompositeCost,
    parse_cost_string,
    pay_cost,
)
from mtg_engine.models.game import (
    GameState, PlayerState, Card, Permanent, ManaPool, Phase, Step,
)


def _make_game_state(controller_name: str = "Player1") -> GameState:
    """Create a minimal game state for testing."""
    player = PlayerState(
        name=controller_name,
        life=20,
        mana_pool=ManaPool(W=2, U=2, B=2, R=2, G=2, C=4),
        hand=[Card(name=f"Card{i}", type_line="Creature") for i in range(5)],
        library=[Card(name=f"LibraryCard{i}", type_line="Creature") for i in range(20)],
        graveyard=[],
        exile=[],
    )
    return GameState(
        game_id="test",
        seed=42,
        players=[player],
        battlefield=[],
        stack=[],
        pending_triggers=[],
        active_player=controller_name,
        priority_holder=controller_name,
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        turn=1,
    )


def _make_permanent(controller: str = "Player1", tapped: bool = False) -> Permanent:
    """Create a test permanent."""
    import uuid
    return Permanent(
        id=str(uuid.uuid4()),
        card=Card(name="TestCreature", type_line="Creature"),
        controller=controller,
        tapped=tapped,
        counters={},
    )


# =====================================================================
# ManaCost tests
# =====================================================================

def test_mana_cost_white():
    cost = ManaCost("W")
    gs = _make_game_state()
    assert cost.can_pay(gs, "Player1")
    gs = cost.pay(gs, "Player1")
    assert gs.players[0].mana_pool.W == 1


def test_mana_cost_multi_color():
    cost = ManaCost("WUB")
    gs = _make_game_state()
    assert cost.can_pay(gs, "Player1")
    gs = cost.pay(gs, "Player1")
    assert gs.players[0].mana_pool.W == 1
    assert gs.players[0].mana_pool.U == 1
    assert gs.players[0].mana_pool.B == 1


def test_mana_cost_generic():
    cost = ManaCost("2")
    gs = _make_game_state()
    assert cost.can_pay(gs, "Player1")
    gs = cost.pay(gs, "Player1")
    # Generic paid from colorless first
    assert gs.players[0].mana_pool.C == 2


def test_mana_cost_insufficient():
    cost = ManaCost("WWWWWW")
    gs = _make_game_state()
    assert not cost.can_pay(gs, "Player1")


def test_mana_cost_colorless():
    cost = ManaCost("C")
    gs = _make_game_state()
    assert cost.can_pay(gs, "Player1")
    gs = cost.pay(gs, "Player1")
    assert gs.players[0].mana_pool.C == 3


def test_mana_cost_description():
    cost = ManaCost("WW")
    assert cost.cost_type == CostType.MANA
    assert "WW" in cost.description


# =====================================================================
# TapCost tests
# =====================================================================

def test_tap_cost_can_pay_untapped():
    perm = _make_permanent(tapped=False)
    cost = TapCost()
    gs = _make_game_state()
    assert cost.can_pay(gs, "Player1", perm)


def test_tap_cost_cannot_pay_tapped():
    perm = _make_permanent(tapped=True)
    cost = TapCost()
    gs = _make_game_state()
    assert not cost.can_pay(gs, "Player1", perm)


def test_tap_cost_pays():
    perm = _make_permanent(tapped=False)
    cost = TapCost()
    gs = _make_game_state()
    gs = cost.pay(gs, "Player1", perm)
    assert perm.tapped


def test_tap_cost_description():
    cost = TapCost()
    assert cost.cost_type == CostType.TAP
    assert cost.description == "{T}"


# =====================================================================
# SacrificeCost tests
# =====================================================================

def test_sacrifice_cost_can_pay():
    perm = _make_permanent()
    gs = _make_game_state()
    gs.battlefield.append(perm)
    cost = SacrificeCost(perm.id)
    assert cost.can_pay(gs, "Player1")


def test_sacrifice_cost_pays():
    perm = _make_permanent()
    gs = _make_game_state()
    gs.battlefield.append(perm)
    cost = SacrificeCost(perm.id)
    gs = cost.pay(gs, "Player1")
    assert len(gs.battlefield) == 0
    assert len(gs.players[0].graveyard) == 1


def test_sacrifice_cost_wrong_controller():
    perm = _make_permanent(controller="Player2")
    gs = _make_game_state()
    gs.battlefield.append(perm)
    cost = SacrificeCost(perm.id)
    assert not cost.can_pay(gs, "Player1")


# =====================================================================
# ExileCost tests
# =====================================================================

def test_exile_cost_from_hand():
    gs = _make_game_state()
    cost = ExileCost(count=2, from_zone="hand")
    assert cost.can_pay(gs, "Player1")
    gs = cost.pay(gs, "Player1")
    assert len(gs.players[0].hand) == 3
    assert len(gs.players[0].exile) == 2


def test_exile_cost_insufficient():
    gs = _make_game_state()
    cost = ExileCost(count=10, from_zone="hand")
    assert not cost.can_pay(gs, "Player1")


# =====================================================================
# DiscardCost tests
# =====================================================================

def test_discard_cost():
    gs = _make_game_state()
    cost = DiscardCost(count=1)
    assert cost.can_pay(gs, "Player1")
    gs = cost.pay(gs, "Player1")
    assert len(gs.players[0].hand) == 4
    assert len(gs.players[0].graveyard) == 1


def test_discard_cost_insufficient():
    gs = _make_game_state()
    cost = DiscardCost(count=10)
    assert not cost.can_pay(gs, "Player1")


# =====================================================================
# LifeCost tests
# =====================================================================

def test_life_cost_can_pay():
    gs = _make_game_state()
    cost = LifeCost(amount=2)
    assert cost.can_pay(gs, "Player1")
    gs = cost.pay(gs, "Player1")
    assert gs.players[0].life == 18


def test_life_cost_cannot_pay():
    gs = _make_game_state()
    gs.players[0].life = 1
    cost = LifeCost(amount=2)
    assert not cost.can_pay(gs, "Player1")


# =====================================================================
# LoyaltyCost tests
# =====================================================================

def test_loyalty_cost_positive():
    perm = _make_permanent()
    perm.counters["loyalty"] = 5
    cost = LoyaltyCost(amount=1)
    gs = _make_game_state()
    assert cost.can_pay(gs, "Player1", perm)
    gs = cost.pay(gs, "Player1", perm)
    assert perm.counters["loyalty"] == 6


def test_loyalty_cost_negative():
    perm = _make_permanent()
    perm.counters["loyalty"] = 5
    cost = LoyaltyCost(amount=-2)
    gs = _make_game_state()
    assert cost.can_pay(gs, "Player1", perm)
    gs = cost.pay(gs, "Player1", perm)
    assert perm.counters["loyalty"] == 3


def test_loyalty_cost_negative_insufficient():
    perm = _make_permanent()
    perm.counters["loyalty"] = 1
    cost = LoyaltyCost(amount=-2)
    gs = _make_game_state()
    assert not cost.can_pay(gs, "Player1", perm)


# =====================================================================
# CompositeCost tests
# =====================================================================

def test_composite_cost():
    gs = _make_game_state()
    composite = CompositeCost([ManaCost("W"), LifeCost(amount=2)])
    assert composite.can_pay(gs, "Player1")
    gs = composite.pay(gs, "Player1")
    assert gs.players[0].mana_pool.W == 1
    assert gs.players[0].life == 18


def test_composite_cost_one_fails():
    gs = _make_game_state()
    composite = CompositeCost([ManaCost("W"), LifeCost(amount=100)])
    assert not composite.can_pay(gs, "Player1")


# =====================================================================
# parse_cost_string tests
# =====================================================================

def test_parse_tap_cost():
    costs = parse_cost_string("{T}")
    assert len(costs) == 1
    assert isinstance(costs[0], TapCost)


def test_parse_mana_cost():
    costs = parse_cost_string("{W}{W}")
    assert len(costs) == 1
    assert isinstance(costs[0], ManaCost)


def test_parse_combined_cost():
    costs = parse_cost_string("{T}{W}")
    assert len(costs) == 2
    types = [c.cost_type for c in costs]
    assert CostType.TAP in types
    assert CostType.MANA in types


def test_parse_generic_mana():
    costs = parse_cost_string("{2}{W}")
    assert len(costs) == 1
    assert isinstance(costs[0], ManaCost)


# =====================================================================
# Integration: pay_cost helper
# =====================================================================

def test_pay_cost_success():
    gs = _make_game_state()
    perm = _make_permanent(tapped=False)
    cost = TapCost()
    gs = pay_cost(gs, "Player1", cost, perm)
    assert perm.tapped


def test_pay_cost_failure():
    gs = _make_game_state()
    perm = _make_permanent(tapped=True)
    cost = TapCost()
    try:
        pay_cost(gs, "Player1", cost, perm)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
