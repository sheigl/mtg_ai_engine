"""Tests for ETB keyword triggers."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.ability.keywords.etb import EtbKeyword, LandfallKeyword
from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, Permanent,
)


def _make_game_with_perm(oracle: str, type_line: str = "Creature — Elf") -> tuple[GameState, Permanent]:
    """Create a game with a permanent that has the given oracle text."""
    card = Card(
        name="Test Card",
        type_line=type_line,
        oracle_text=oracle,
        power="1",
        toughness="1",
    )
    perm = Permanent(card=card, controller="p1")
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
        battlefield=[perm],
    )
    return gs, perm


def test_etb_keyword_applies_self_referential():
    """ETB keyword detects self-referential triggers."""
    gs, perm = _make_game_with_perm("When this enters the battlefield, draw a card.")
    kw = EtbKeyword(effect="draw a card", trigger_type="self")
    assert kw.applies(gs, perm) is True


def test_etb_keyword_applies_any_creature():
    """ETB keyword detects 'whenever a creature enters' triggers."""
    gs, perm = _make_game_with_perm("Whenever a creature enters the battlefield, put a +1/+1 counter on this.")
    kw = EtbKeyword(effect="put a +1/+1 counter", trigger_type="any", card_type_filter="creature")
    assert kw.applies(gs, perm) is True


def test_etb_keyword_does_not_apply():
    """ETB keyword returns False for cards without ETB."""
    gs, perm = _make_game_with_perm("Flying.")
    kw = EtbKeyword(effect="draw a card")
    assert kw.applies(gs, perm) is False


def test_etb_create_trigger_self():
    """ETB creates trigger for self-referential event."""
    gs, perm = _make_game_with_perm("When this enters the battlefield, draw a card.")
    kw = EtbKeyword(effect="draw a card", trigger_type="self")

    trigger = kw.create_trigger(gs, perm, perm)
    assert trigger is not None
    assert trigger.trigger_type == "etb"
    assert "draw a card" in trigger.effect_description


def test_etb_create_trigger_self_no_match():
    """ETB self trigger doesn't fire for other cards."""
    gs, perm = _make_game_with_perm("When this enters the battlefield, draw a card.")
    kw = EtbKeyword(effect="draw a card", trigger_type="self")

    other_card = Card(name="Other", type_line="Creature", power="1", toughness="1")
    other_perm = Permanent(card=other_card, controller="p1")

    trigger = kw.create_trigger(gs, perm, other_perm)
    assert trigger is None


def test_etb_create_trigger_type_filter():
    """ETB type filter only matches correct card types."""
    gs, perm = _make_game_with_perm("Whenever a creature enters, draw a card.")
    kw = EtbKeyword(effect="draw a card", trigger_type="any", card_type_filter="creature")

    creature = Card(name="Bear", type_line="Creature — Bear", power="2", toughness="2")
    creature_perm = Permanent(card=creature, controller="p1")
    trigger = kw.create_trigger(gs, perm, creature_perm)
    assert trigger is not None

    land = Card(name="Forest", type_line="Basic Land — Forest")
    land_perm = Permanent(card=land, controller="p1")
    trigger = kw.create_trigger(gs, perm, land_perm)
    assert trigger is None


def test_etb_optional_trigger():
    """ETB marks 'you may' triggers as optional."""
    gs, perm = _make_game_with_perm("When this enters, you may draw a card.")
    kw = EtbKeyword(effect="you may draw a card", trigger_type="self")

    trigger = kw.create_trigger(gs, perm, perm)
    assert trigger is not None
    assert trigger.is_optional is True


def test_etb_apply_returns_state():
    """ETB apply returns the game state."""
    gs, perm = _make_game_with_perm("When this enters, draw a card.")
    kw = EtbKeyword(effect="draw a card")
    result = kw.apply(gs, perm)
    assert result is gs


def test_landfall_keyword_applies():
    """Landfall detects landfall triggers."""
    oracle = "Landfall — Whenever a land enters the battlefield under your control, put a +1/+1 counter on this creature."
    gs, perm = _make_game_with_perm(oracle)
    kw = LandfallKeyword(effect="put a +1/+1 counter on this creature")
    assert kw.applies(gs, perm) is True


def test_landfall_only_triggers_for_lands():
    """Landfall only creates triggers for land cards."""
    gs, perm = _make_game_with_perm("Landfall — Whenever a land enters, put a counter on this.")
    kw = LandfallKeyword(effect="put a counter on this")

    land = Card(name="Forest", type_line="Basic Land — Forest")
    land_perm = Permanent(card=land, controller="p1")
    trigger = kw.create_trigger(gs, perm, land_perm)
    assert trigger is not None
    assert trigger.trigger_type == "landfall"

    creature = Card(name="Bear", type_line="Creature — Bear", power="2", toughness="2")
    creature_perm = Permanent(card=creature, controller="p1")
    trigger = kw.create_trigger(gs, perm, creature_perm)
    assert trigger is None


def test_landfall_description():
    """Landfall returns proper description."""
    kw = LandfallKeyword(effect="draw a card")
    desc = kw.get_trigger_description()
    assert "Landfall" in desc
    assert "draw a card" in desc
