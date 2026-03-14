import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card
from mtg_engine.engine.zones import (
    move_card_to_zone,
    move_permanent_to_zone,
    put_permanent_onto_battlefield,
    draw_card,
    get_player,
)


def _make_game() -> GameState:
    card = Card(name="Forest", type_line="Basic Land — Forest")
    p1 = PlayerState(name="p1", library=[card])
    p2 = PlayerState(name="p2")
    return GameState(
        game_id="test", seed=1, active_player="p1", priority_holder="p1",
        players=[p1, p2]
    )


def test_draw_card_removes_from_library():
    gs = _make_game()
    assert len(get_player(gs, "p1").library) == 1
    gs, card = draw_card(gs, "p1")
    assert card is not None
    assert card.name == "Forest"
    assert len(get_player(gs, "p1").library) == 0
    assert len(get_player(gs, "p1").hand) == 1


def test_draw_empty_returns_none():
    gs = _make_game()
    gs, _ = draw_card(gs, "p1")
    gs, card = draw_card(gs, "p1")
    assert card is None


def test_move_card_hand_to_graveyard():
    gs = _make_game()
    gs, card = draw_card(gs, "p1")
    gs = move_card_to_zone(gs, card, "hand", "graveyard", "p1")
    assert len(get_player(gs, "p1").hand) == 0
    assert len(get_player(gs, "p1").graveyard) == 1


def test_put_permanent_onto_battlefield():
    gs = _make_game()
    card = Card(name="Grizzly Bears", type_line="Creature — Bear", power="2", toughness="2")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    assert len(gs.battlefield) == 1
    assert gs.battlefield[0].card.name == "Grizzly Bears"
    assert gs.battlefield[0].controller == "p1"


def test_token_does_not_go_to_graveyard():
    gs = _make_game()
    card = Card(name="Saproling", type_line="Creature — Saproling", power="1", toughness="1")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1", is_token=True)
    gs = move_permanent_to_zone(gs, perm, "graveyard")
    assert len(gs.battlefield) == 0
    assert len(get_player(gs, "p1").graveyard) == 0  # token ceases to exist (CR 704.5d)


def test_move_card_to_library_top():
    """REQ-G08: card placed at top of library is at index 0."""
    gs = _make_game()
    gs, card = draw_card(gs, "p1")
    extra = Card(name="Island", type_line="Basic Land — Island")
    get_player(gs, "p1").library.append(extra)
    gs = move_card_to_zone(gs, card, "hand", "library", "p1", position="top")
    assert get_player(gs, "p1").library[0].name == "Forest"


def test_move_card_to_library_bottom():
    """REQ-G08: card placed at bottom of library is at last index."""
    gs = _make_game()
    gs, card = draw_card(gs, "p1")
    extra = Card(name="Island", type_line="Basic Land — Island")
    get_player(gs, "p1").library.append(extra)
    gs = move_card_to_zone(gs, card, "hand", "library", "p1", position="bottom")
    lib = get_player(gs, "p1").library
    assert lib[-1].name == "Forest"


def test_card_not_in_two_zones():
    """REQ-G07: after move, card exists in exactly one zone."""
    gs = _make_game()
    gs, card = draw_card(gs, "p1")
    gs = move_card_to_zone(gs, card, "hand", "graveyard", "p1")
    hand_ids = [c.id for c in get_player(gs, "p1").hand]
    graveyard_ids = [c.id for c in get_player(gs, "p1").graveyard]
    assert card.id not in hand_ids
    assert card.id in graveyard_ids


def test_permanent_enters_battlefield_summoning_sick():
    """Creature entering battlefield should have summoning sickness."""
    gs = _make_game()
    card = Card(name="Grizzly Bears", type_line="Creature — Bear", power="2", toughness="2")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    assert perm.summoning_sick is True
