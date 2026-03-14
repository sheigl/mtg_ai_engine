import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card, ManaPool
from mtg_engine.engine.stack import cast_spell, resolve_top
from mtg_engine.engine.zones import put_permanent_onto_battlefield


def _make_game_with_mana(p1_mana: ManaPool | None = None) -> GameState:
    bolt = Card(
        name="Lightning Bolt",
        type_line="Instant",
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        mana_cost="{R}",
    )
    p1 = PlayerState(
        name="p1", life=20, hand=[bolt], mana_pool=p1_mana or ManaPool(R=1)
    )
    p2 = PlayerState(name="p2", life=20)
    return GameState(
        game_id="test", seed=1, active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
    )


def test_cast_lightning_bolt_goes_to_stack():
    gs = _make_game_with_mana(ManaPool(R=1))
    bolt_id = gs.players[0].hand[0].id
    gs = cast_spell(gs, "p1", bolt_id, targets=["p2"], mana_payment={"R": 1})
    assert len(gs.stack) == 1
    assert gs.stack[0].source_card.name == "Lightning Bolt"
    assert len(gs.players[0].hand) == 0  # removed from hand
    assert gs.players[0].mana_pool.R == 0  # cost paid


def test_cast_bolt_at_instant_speed_priority_stays():
    gs = _make_game_with_mana(ManaPool(R=1))
    bolt_id = gs.players[0].hand[0].id
    gs = cast_spell(gs, "p1", bolt_id, targets=["p2"], mana_payment={"R": 1})
    # Priority returns to active player after casting (REQ-S01)
    assert gs.priority_holder == "p1"


def test_resolve_lightning_bolt_damages_player():
    gs = _make_game_with_mana(ManaPool(R=1))
    bolt_id = gs.players[0].hand[0].id
    gs = cast_spell(gs, "p1", bolt_id, targets=["p2"], mana_payment={"R": 1})
    gs = resolve_top(gs)
    assert gs.players[1].life == 17  # 20 - 3
    assert len(gs.stack) == 0
    assert len(gs.players[0].graveyard) == 1  # bolt in graveyard


def test_resolve_bolt_damages_creature():
    gs = _make_game_with_mana(ManaPool(R=1))
    bear_card = Card(
        name="Grizzly Bears", type_line="Creature — Bear", power="2", toughness="2"
    )
    gs, bear_perm = put_permanent_onto_battlefield(gs, bear_card, "p2")
    bolt_id = gs.players[0].hand[0].id
    gs = cast_spell(gs, "p1", bolt_id, targets=[bear_perm.id], mana_payment={"R": 1})
    gs = resolve_top(gs)
    # Bear has 3 damage marked (bolt deals 3, toughness is 2) — SBA kills it
    from mtg_engine.engine.sba import check_and_apply_sbas
    gs, events = check_and_apply_sbas(gs)
    assert len(gs.battlefield) == 0  # bear is dead


def test_cast_sorcery_requires_main_phase():
    sorcery = Card(
        name="Terror",
        type_line="Sorcery",
        oracle_text="Destroy target creature.",
        mana_cost="{1}{B}",
    )
    p1 = PlayerState(name="p1", hand=[sorcery], mana_pool=ManaPool(B=1, C=1))
    p2 = PlayerState(name="p2")
    # Combat phase — should fail (not main phase)
    gs = GameState(
        game_id="test", seed=1, active_player="p1", priority_holder="p1",
        phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS,
        players=[p1, p2],
    )
    try:
        gs = cast_spell(gs, "p1", sorcery.id, targets=[], mana_payment={"B": 1, "C": 1})
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_cannot_cast_without_priority():
    gs = _make_game_with_mana(ManaPool(R=1))
    gs.priority_holder = "p2"
    bolt_id = gs.players[0].hand[0].id
    try:
        cast_spell(gs, "p1", bolt_id, targets=["p2"], mana_payment={"R": 1})
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_cannot_cast_with_insufficient_mana():
    gs = _make_game_with_mana(ManaPool(G=1))  # wrong color
    bolt_id = gs.players[0].hand[0].id
    try:
        cast_spell(gs, "p1", bolt_id, targets=["p2"], mana_payment={"G": 1})
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_cast_instant_at_non_main_phase():
    """Instants can be cast at any time with priority (not just main phase)."""
    bolt = Card(
        name="Lightning Bolt",
        type_line="Instant",
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        mana_cost="{R}",
    )
    p1 = PlayerState(name="p1", life=20, hand=[bolt], mana_pool=ManaPool(R=1))
    p2 = PlayerState(name="p2", life=20)
    # During combat — instants are fine
    gs = GameState(
        game_id="test", seed=1, active_player="p1", priority_holder="p1",
        phase=Phase.COMBAT, step=Step.DECLARE_BLOCKERS,
        players=[p1, p2],
    )
    gs = cast_spell(gs, "p1", bolt.id, targets=["p2"], mana_payment={"R": 1})
    assert len(gs.stack) == 1


def test_permanent_spell_enters_battlefield():
    """Resolving a creature spell puts it on the battlefield."""
    bear = Card(
        name="Grizzly Bears",
        type_line="Creature — Bear",
        power="2", toughness="2",
        mana_cost="{1}{G}",
    )
    p1 = PlayerState(name="p1", life=20, hand=[bear], mana_pool=ManaPool(G=2))
    p2 = PlayerState(name="p2", life=20)
    gs = GameState(
        game_id="test", seed=1, active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
    )
    gs = cast_spell(gs, "p1", bear.id, targets=[], mana_payment={"G": 2})
    assert len(gs.stack) == 1
    gs = resolve_top(gs)
    assert len(gs.battlefield) == 1
    assert gs.battlefield[0].card.name == "Grizzly Bears"
    assert len(gs.players[0].hand) == 0
