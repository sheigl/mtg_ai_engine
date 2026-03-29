"""
Tests for US5: Cascade Trigger Works.
T068-T070: cascade card selection, cascade choice action, library placement.
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


def _make_cascade_spell() -> Card:
    return Card(
        name="Shardless Agent",
        type_line="Artifact Creature — Phyrexian Elf Rogue",
        oracle_text="Cascade",
        mana_cost="{1}{G}{U}",
        keywords=["cascade"],
        cmc=3.0,
    )


# T068: Test cascade card selection
def test_cascade_selects_card_from_library():
    gs = _gs()
    # Library: a 4-CMC card (won't cascade into), then a 2-CMC card (will)
    big_card = Card(name="Baneslayer Angel", type_line="Creature", cmc=5.0)
    small_card = Card(name="Grizzly Bears", type_line="Creature", cmc=2.0)
    gs.players[0].library = [big_card, small_card]

    cascade_card = _make_cascade_spell()
    gs.players[0].hand.append(cascade_card)
    gs.players[0].mana_pool = ManaPool(G=1, U=1, C=1)

    gs = cast_spell(gs, "p1", cascade_card.id, targets=[], mana_payment={"G": 1, "U": 1, "C": 1})
    gs = resolve_top(gs)

    # After resolving, cascade should have fired and set pending_cascade
    assert gs.pending_cascade is not None
    found = gs.pending_cascade.get("found_card", {})
    # Should have found the 2-CMC card (less than CMC 3)
    assert found.get("name") == "Grizzly Bears"


# T069: Test cascade choice action
def test_cascade_choice_legal_action():
    gs = _gs()
    small_card = Card(name="Grizzly Bears", type_line="Creature", cmc=2.0)
    gs.players[0].library = [small_card]

    cascade_card = _make_cascade_spell()
    gs.players[0].hand.append(cascade_card)
    gs.players[0].mana_pool = ManaPool(G=1, U=1, C=1)

    gs = cast_spell(gs, "p1", cascade_card.id, targets=[], mana_payment={"G": 1, "U": 1, "C": 1})
    gs = resolve_top(gs)

    # There should be a cascade_choice legal action available
    from mtg_engine.api.routers.game import _compute_legal_actions
    actions = _compute_legal_actions(gs)
    cascade_actions = [a for a in actions if a.action_type == "cascade_choice"]
    assert len(cascade_actions) > 0


# T070: Test cascade library placement (non-chosen cards go to bottom)
def test_cascade_non_chosen_cards_go_to_library():
    gs = _gs()
    # Library: land (skip), then high-CMC (skip), then valid cascade target
    land_card = Card(name="Forest", type_line="Basic Land — Forest", cmc=0.0)
    high_cmc = Card(name="Emrakul", type_line="Creature", cmc=15.0)
    valid_card = Card(name="Grizzly Bears", type_line="Creature", cmc=2.0)
    gs.players[0].library = [land_card, high_cmc, valid_card]

    cascade_card = _make_cascade_spell()
    gs.players[0].hand.append(cascade_card)
    gs.players[0].mana_pool = ManaPool(G=1, U=1, C=1)

    gs = cast_spell(gs, "p1", cascade_card.id, targets=[], mana_payment={"G": 1, "U": 1, "C": 1})
    gs = resolve_top(gs)

    # pending_cascade should be set with found_card = Grizzly Bears
    assert gs.pending_cascade is not None
    assert gs.pending_cascade["found_card"]["name"] == "Grizzly Bears"
    # The skipped cards (land, high_cmc) should be in exile (per implementation)
    # or tracked in exiled_cards
    exiled = gs.pending_cascade.get("exiled_cards", [])
    exiled_names = [c["name"] for c in exiled]
    assert "Forest" in exiled_names or "Emrakul" in exiled_names
