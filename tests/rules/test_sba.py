import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card, Permanent
from mtg_engine.engine.sba import check_and_apply_sbas
from mtg_engine.engine.zones import put_permanent_onto_battlefield, draw_card


def _make_game() -> GameState:
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    return GameState(
        game_id="test", seed=1, active_player="p1", priority_holder="p1",
        players=[p1, p2]
    )


def test_player_at_zero_life_loses():
    gs = _make_game()
    gs.players[0].life = 0
    gs, events = check_and_apply_sbas(gs)
    assert gs.players[0].has_lost
    sba_types = [e.sba_type for e in events]
    assert "life_loss" in sba_types


def test_player_at_negative_life_loses():
    gs = _make_game()
    gs.players[1].life = -5
    gs, events = check_and_apply_sbas(gs)
    assert gs.players[1].has_lost
    assert any(e.sba_type == "life_loss" for e in events)


def test_creature_lethal_damage_dies():
    gs = _make_game()
    card = Card(name="Grizzly Bears", type_line="Creature — Bear", power="2", toughness="2")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    perm.damage_marked = 2  # lethal (equals toughness)
    gs, events = check_and_apply_sbas(gs)
    assert len(gs.battlefield) == 0
    assert any(e.sba_type == "lethal_damage" for e in events)


def test_creature_toughness_zero_dies():
    gs = _make_game()
    card = Card(name="Cursed", type_line="Creature — Horror", power="2", toughness="2")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    perm.counters["-1/-1"] = 2  # effective toughness becomes 0
    gs, events = check_and_apply_sbas(gs)
    assert len(gs.battlefield) == 0
    assert any(e.sba_type == "toughness_zero" for e in events)


def test_creature_toughness_negative_dies():
    gs = _make_game()
    card = Card(name="Weakling", type_line="Creature — Horror", power="1", toughness="1")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    perm.counters["-1/-1"] = 3  # effective toughness = 1 - 3 = -2
    gs, events = check_and_apply_sbas(gs)
    assert len(gs.battlefield) == 0
    assert any(e.sba_type == "toughness_zero" for e in events)


def test_legend_rule():
    gs = _make_game()
    card1 = Card(
        name="Jace, the Mind Sculptor",
        type_line="Legendary Creature — Human Wizard",
        power="0", toughness="2",
    )
    card2 = Card(
        name="Jace, the Mind Sculptor",
        type_line="Legendary Creature — Human Wizard",
        power="0", toughness="2",
    )
    gs, p1 = put_permanent_onto_battlefield(gs, card1, "p1")
    time.sleep(0.01)  # ensure distinct timestamps
    gs, p2 = put_permanent_onto_battlefield(gs, card2, "p1")
    gs, events = check_and_apply_sbas(gs)
    assert len(gs.battlefield) == 1  # one kept (most recent)
    assert any(e.sba_type == "legend_rule" for e in events)


def test_legend_rule_different_players_ok():
    """Legend rule only applies per controller; different controllers can each have one."""
    gs = _make_game()
    card1 = Card(
        name="Jace, the Mind Sculptor",
        type_line="Legendary Creature — Human Wizard",
        power="0", toughness="2",
    )
    card2 = Card(
        name="Jace, the Mind Sculptor",
        type_line="Legendary Creature — Human Wizard",
        power="0", toughness="2",
    )
    gs, _ = put_permanent_onto_battlefield(gs, card1, "p1")
    gs, _ = put_permanent_onto_battlefield(gs, card2, "p2")
    gs, events = check_and_apply_sbas(gs)
    assert len(gs.battlefield) == 2  # both survive (different controllers)
    assert not any(e.sba_type == "legend_rule" for e in events)


def test_counter_annihilation():
    gs = _make_game()
    card = Card(name="Creature", type_line="Creature — Beast", power="2", toughness="2")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    perm.counters["+1/+1"] = 3
    perm.counters["-1/-1"] = 2
    gs, events = check_and_apply_sbas(gs)
    perm = gs.battlefield[0]
    assert perm.counters.get("+1/+1", 0) == 1
    assert perm.counters.get("-1/-1", 0) == 0
    assert any(e.sba_type == "counter_annihilation" for e in events)


def test_poison_counters():
    gs = _make_game()
    gs.players[0].poison_counters = 10
    gs, events = check_and_apply_sbas(gs)
    assert gs.players[0].has_lost
    assert any(e.sba_type == "poison" for e in events)


def test_indestructible_survives_lethal_damage():
    gs = _make_game()
    card = Card(
        name="God",
        type_line="Creature — God",
        power="5", toughness="7",
        keywords=["indestructible"],
    )
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    perm.damage_marked = 10
    gs, events = check_and_apply_sbas(gs)
    assert len(gs.battlefield) == 1  # survives
    assert not any(e.sba_type == "lethal_damage" for e in events)


def test_deathtouch_destroys_creature():
    """CR 704.5h: creature dealt damage by deathtouch source is destroyed."""
    gs = _make_game()
    card = Card(name="Rhino", type_line="Creature — Rhino", power="4", toughness="4")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    perm.damage_marked = 1
    perm.counters["__deathtouch_damage__"] = 1  # any damage from deathtouch source
    gs, events = check_and_apply_sbas(gs)
    assert len(gs.battlefield) == 0
    assert any(e.sba_type == "deathtouch" for e in events)


def test_planeswalker_zero_loyalty():
    """CR 704.5i: planeswalker with 0 loyalty goes to graveyard."""
    gs = _make_game()
    card = Card(
        name="Jace Beleren",
        type_line="Legendary Planeswalker — Jace",
        loyalty="3",
    )
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    perm.counters["loyalty"] = 0
    gs, events = check_and_apply_sbas(gs)
    assert len(gs.battlefield) == 0
    assert any(e.sba_type == "planeswalker_loyalty" for e in events)


def test_game_over_when_player_loses():
    """Game is marked over when a player loses."""
    gs = _make_game()
    gs.players[0].life = 0
    gs, events = check_and_apply_sbas(gs)
    assert gs.is_game_over
    assert gs.winner == "p2"


def test_deck_out_loss():
    """CR 704.5b: player who draws from empty library loses."""
    gs = _make_game()
    # p1 has empty library
    gs.players[0].library = []
    gs, card = draw_card(gs, "p1")
    assert card is None
    assert gs.players[0].has_lost
    # SBA check should mark game over
    gs, events = check_and_apply_sbas(gs)
    assert gs.is_game_over
    assert gs.winner == "p2"


def test_draw_with_cards_does_not_lose():
    """Drawing from a non-empty library should not trigger loss."""
    from mtg_engine.models.game import Card as GameCard
    gs = _make_game()
    card = GameCard(name="Plains", type_line="Basic Land — Plains")
    gs.players[0].library = [card]
    gs, drawn = draw_card(gs, "p1")
    assert drawn is not None
    assert not gs.players[0].has_lost
    gs, events = check_and_apply_sbas(gs)
    assert not gs.is_game_over
