"""
Tests for US4: Modal Spells Apply Only Chosen Mode.
T062-T063: single mode selection, multiple mode selection.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card, ManaPool
from mtg_engine.engine.stack import cast_spell, resolve_top
from mtg_engine.engine.zones import put_permanent_onto_battlefield


def _gs() -> GameState:
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    return GameState(
        game_id="test", seed=1, active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
    )


# T062: Test single mode selection
def test_single_mode_selection_draw_only():
    gs = _gs()
    for i in range(5):
        gs.players[0].library.append(Card(name=f"Card{i}", type_line="Creature"))
    hand_before = len(gs.players[0].hand)
    charm = Card(
        name="Esper Charm",
        type_line="Instant",
        oracle_text="Choose one — • Draw 2 cards. • Destroy target enchantment. • Target player discards 2 cards.",
        mana_cost="{W}{U}{B}",
    )
    gs.players[0].hand.append(charm)
    gs.players[0].mana_pool = ManaPool(W=1, U=1, B=1)
    # Mode texts after split: [0]="Choose one —", [1]="Draw 2 cards.", [2]="Destroy...", [3]="discard..."
    # Choose mode 1 (draw 2 cards) — discard should NOT apply
    gs = cast_spell(
        gs, "p1", charm.id,
        targets=[],
        mana_payment={"W": 1, "U": 1, "B": 1},
        modes_chosen=[1],
    )
    gs = resolve_top(gs)
    # Drew 2 cards
    assert len(gs.players[0].hand) == hand_before + 2
    # Life did not change
    assert gs.players[0].life == 20


def test_single_mode_selection_destroy_only():
    gs = _gs()
    bear = Card(name="Grizzly Bears", type_line="Creature — Bear", power="2", toughness="2")
    gs, bear_perm = put_permanent_onto_battlefield(gs, bear, "p2")
    charm = Card(
        name="Putrefy",
        type_line="Instant",
        oracle_text="Choose one — • Destroy target creature. • Draw 2 cards.",
        mana_cost="{1}{B}{G}",
    )
    gs.players[0].hand.append(charm)
    gs.players[0].mana_pool = ManaPool(B=1, G=1, C=1)
    # Mode texts: [0]="Choose one —", [1]="Destroy target creature.", [2]="Draw 2 cards."
    # Choose mode 1 (destroy target creature)
    gs = cast_spell(
        gs, "p1", charm.id,
        targets=[bear_perm.id],
        mana_payment={"B": 1, "G": 1, "C": 1},
        modes_chosen=[1],
    )
    gs = resolve_top(gs)
    # Bear destroyed
    assert not any(p.id == bear_perm.id for p in gs.battlefield)
    # Hand didn't grow (mode 1 not chosen)
    assert len(gs.players[0].hand) == 0


# T063: Test multiple mode selection
def test_multiple_mode_selection():
    gs = _gs()
    for i in range(5):
        gs.players[0].library.append(Card(name=f"Card{i}", type_line="Creature"))
    hand_before = len(gs.players[0].hand)
    gs.players[0].life = 15
    charm = Card(
        name="Cryptic Command",
        type_line="Instant",
        oracle_text="Choose two — • Counter target spell. • Draw 2 cards. • You gain 3 life.",
        mana_cost="{1}{U}{U}{U}",
    )
    gs.players[0].hand.append(charm)
    gs.players[0].mana_pool = ManaPool(U=3, C=1)
    # Mode texts: [0]="Choose two —", [1]="Counter target spell.", [2]="Draw 2 cards.", [3]="You gain 3 life."
    # Choose modes 2 (draw 2) and 3 (gain 3 life)
    gs = cast_spell(
        gs, "p1", charm.id,
        targets=[],
        mana_payment={"U": 3, "C": 1},
        modes_chosen=[2, 3],
    )
    gs = resolve_top(gs)
    # Drew 2 cards (mode 1)
    assert len(gs.players[0].hand) == hand_before + 2
    # Gained 3 life (mode 2)
    assert gs.players[0].life == 18
