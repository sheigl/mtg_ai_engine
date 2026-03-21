import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import GameState, PlayerState, Card
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.engine.replacement import GameEvent, process_event, apply_damage_event


def _make_game() -> GameState:
    p1 = PlayerState(name="p1")
    p2 = PlayerState(name="p2")
    return GameState(game_id="t", seed=1, active_player="p1", priority_holder="p1", players=[p1, p2])


def test_shield_counter_prevents_destruction():
    """Shield counter: removed instead of creature being destroyed."""
    gs = _make_game()
    card = Card(name="Knight", type_line="Creature — Human Knight", power="2", toughness="2")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    perm.counters["shield"] = 1

    event = GameEvent(event_type="destroy", target_id=perm.id)
    event, gs = process_event(event, gs)

    assert event.cancelled
    assert perm.counters.get("shield", 0) == 0
    # Permanent still on battlefield
    assert any(p.id == perm.id for p in gs.battlefield)


def test_no_replacement_no_shield():
    """Without shield, destroy event is not cancelled."""
    gs = _make_game()
    card = Card(name="Creature", type_line="Creature — Beast", power="2", toughness="2")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")

    event = GameEvent(event_type="destroy", target_id=perm.id)
    event, gs = process_event(event, gs)

    assert not event.cancelled


def test_damage_to_player_reduces_life():
    gs = _make_game()
    gs = apply_damage_event(gs, "Lightning Bolt", [], "p2", 3)
    assert gs.players[1].life == 17


def test_infect_damage_to_creature_as_counters():
    gs = _make_game()
    card = Card(name="Creature", type_line="Creature — Beast", power="2", toughness="2")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    gs = apply_damage_event(gs, "Infect Source", ["infect"], perm.id, 2)
    assert perm.counters.get("-1/-1", 0) == 2
    assert perm.damage_marked == 0  # no regular damage
