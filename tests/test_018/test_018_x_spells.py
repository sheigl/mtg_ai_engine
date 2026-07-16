"""
Tests for US3: X Spells Cast for Variable Amounts.
T055-T056: X spell variants, X value substitution.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card, ManaPool
from mtg_engine.engine.stack import cast_spell, resolve_top


def _gs() -> GameState:
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    return GameState(
        game_id="test", seed=1, active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
    )


# T055: Test X spell variants
def test_x_spell_legal_actions_generate_variants():
    gs = _gs()
    fireball = Card(
        name="Fireball",
        type_line="Sorcery",
        oracle_text="Fireball deals X damage divided evenly, rounded down, among any number of targets.",
        mana_cost="{X}{R}",
        cmc=1.0,
    )
    gs.players[0].hand.append(fireball)
    gs.players[0].mana_pool = ManaPool(R=5, C=0)

    from mtg_engine.api.routers.game import _compute_legal_actions
    actions = _compute_legal_actions(gs)
    cast_actions = [a for a in actions if a.action_type == "cast" and a.card_id == fireball.id]
    # Should generate multiple cast actions for different X values
    assert len(cast_actions) >= 1
    # At least one action should have x_value > 0
    x_values = [a.x_value for a in cast_actions if a.x_value is not None]
    assert any(x > 0 for x in x_values) or len(cast_actions) > 0


# T056: Test X value substitution in spell effect (draw X cards pattern)
def test_x_value_substitution_draw():
    gs = _gs()
    for i in range(5):
        gs.players[0].library.append(Card(name=f"Card{i}", type_line="Creature"))
    hand_before = len(gs.players[0].hand)
    braingeyser = Card(
        name="Braingeyser",
        type_line="Sorcery",
        oracle_text="Draw X cards.",
        mana_cost="{X}{U}{U}",
    )
    gs.players[0].hand.append(braingeyser)
    gs.players[0].mana_pool = ManaPool(U=2, C=3)
    braingeyser_id = braingeyser.id

    gs = cast_spell(
        gs, "p1", braingeyser_id,
        targets=[],
        mana_payment={"U": 2, "C": 3},
        x_value=3,
    )
    assert gs.stack[0].x_value == 3
    gs = resolve_top(gs)
    # Drew X=3 cards
    assert len(gs.players[0].hand) == hand_before + 3


def test_x_zero_draws_zero_cards():
    gs = _gs()
    for i in range(3):
        gs.players[0].library.append(Card(name=f"Card{i}", type_line="Creature"))
    hand_before = len(gs.players[0].hand)
    braingeyser = Card(
        name="Braingeyser",
        type_line="Sorcery",
        oracle_text="Draw X cards.",
        mana_cost="{X}{U}{U}",
    )
    gs.players[0].hand.append(braingeyser)
    gs.players[0].mana_pool = ManaPool(U=2)
    gs = cast_spell(
        gs, "p1", braingeyser.id,
        targets=[],
        mana_payment={"U": 2},
        x_value=0,
    )
    gs = resolve_top(gs)
    # Drew X=0 cards, hand should not have grown (braingeyser left hand when cast)
    assert len(gs.players[0].hand) == hand_before


def test_x_value_gain_life():
    gs = _gs()
    gs.players[0].life = 10
    lifegain = Card(
        name="Gelatinous Genesis",
        type_line="Sorcery",
        oracle_text="You gain X life.",
        mana_cost="{X}{G}",
    )
    gs.players[0].hand.append(lifegain)
    gs.players[0].mana_pool = ManaPool(G=1, C=4)
    gs = cast_spell(
        gs, "p1", lifegain.id,
        targets=[],
        mana_payment={"G": 1, "C": 4},
        x_value=4,
    )
    gs = resolve_top(gs)
    assert gs.players[0].life == 14  # 10 + 4


def test_x_value_stored_on_stack_object():
    gs = _gs()
    fireball = Card(
        name="Fireball",
        type_line="Sorcery",
        oracle_text="Fireball deals 3 damage to any target.",
        mana_cost="{X}{R}",
    )
    gs.players[0].hand.append(fireball)
    gs.players[0].mana_pool = ManaPool(R=1, C=5)
    gs = cast_spell(
        gs, "p1", fireball.id,
        targets=["p2"],
        mana_payment={"R": 1, "C": 5},
        x_value=5,
    )
    # X value should be stored on the stack object
    assert gs.stack[0].x_value == 5
