"""Tests for LTB keyword triggers."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.ability.keywords.leave import (
    LeaveBattlefieldKeyword,
    DiesKeyword,
    UndyingKeyword,
)
from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, Permanent,
)


def _make_game_with_perm(oracle: str, type_line: str = "Creature — Elf") -> tuple[GameState, Permanent]:
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


def test_ltb_keyword_applies_leaves():
    """LTB detects 'leaves the battlefield' triggers."""
    gs, perm = _make_game_with_perm("When this leaves the battlefield, draw a card.")
    kw = LeaveBattlefieldKeyword(effect="draw a card", trigger_type="self")
    assert kw.applies(gs, perm) is True


def test_ltb_keyword_applies_dies():
    """LTB detects 'dies' triggers."""
    gs, perm = _make_game_with_perm("Whenever this dies, return it to the battlefield.")
    kw = LeaveBattlefieldKeyword(effect="return it", trigger_type="self")
    assert kw.applies(gs, perm) is True


def test_ltb_keyword_does_not_apply():
    """LTB returns False for cards without LTB."""
    gs, perm = _make_game_with_perm("Flying.")
    kw = LeaveBattlefieldKeyword(effect="draw a card")
    assert kw.applies(gs, perm) is False


def test_ltb_create_trigger_self():
    """LTB creates trigger for self-referential event."""
    gs, perm = _make_game_with_perm("When this leaves the battlefield, draw a card.")
    kw = LeaveBattlefieldKeyword(effect="draw a card", trigger_type="self")

    trigger = kw.create_trigger(gs, perm, perm, to_zone="graveyard")
    assert trigger is not None
    assert trigger.trigger_type == "ltb"


def test_ltb_create_trigger_self_no_match():
    """LTB self trigger doesn't fire for other cards."""
    gs, perm = _make_game_with_perm("When this leaves the battlefield, draw a card.")
    kw = LeaveBattlefieldKeyword(effect="draw a card", trigger_type="self")

    other = Card(name="Other", type_line="Creature", power="1", toughness="1")
    other_perm = Permanent(card=other, controller="p1")
    trigger = kw.create_trigger(gs, perm, other_perm, to_zone="graveyard")
    assert trigger is None


def test_ltb_zone_filter():
    """LTB zone filter only matches correct zone."""
    gs, perm = _make_game_with_perm("When this is put into exile, draw a card.")
    kw = LeaveBattlefieldKeyword(effect="draw a card", trigger_type="self", zone_filter="exile")

    trigger = kw.create_trigger(gs, perm, perm, to_zone="exile")
    assert trigger is not None

    trigger = kw.create_trigger(gs, perm, perm, to_zone="graveyard")
    assert trigger is None


def test_dies_keyword_only_graveyard():
    """Dies keyword only triggers for graveyard destination."""
    gs, perm = _make_game_with_perm("Whenever a creature dies, draw a card.")
    kw = DiesKeyword(effect="draw a card")

    creature = Card(name="Bear", type_line="Creature — Bear", power="2", toughness="2")
    creature_perm = Permanent(card=creature, controller="p1")

    trigger = kw.create_trigger(gs, perm, creature_perm, to_zone="graveyard")
    assert trigger is not None

    trigger = kw.create_trigger(gs, perm, creature_perm, to_zone="exile")
    assert trigger is None


def test_undying_no_counters():
    """Undying triggers when creature has no +1/+1 counters."""
    gs, perm = _make_game_with_perm("Undying")
    kw = UndyingKeyword(effect="return with counters")

    trigger = kw.create_trigger(gs, perm, perm, to_zone="graveyard")
    assert trigger is not None


def test_undying_with_counters():
    """Undying does NOT trigger if creature has +1/+1 counters."""
    gs, perm = _make_game_with_perm("Undying")
    perm.counters = {"+1/+1": 1}
    kw = UndyingKeyword(effect="return with counters")

    trigger = kw.create_trigger(gs, perm, perm, to_zone="graveyard")
    assert trigger is None


def test_ltb_optional_trigger():
    """LTB marks 'you may' triggers as optional."""
    gs, perm = _make_game_with_perm("When this leaves, you may draw a card.")
    kw = LeaveBattlefieldKeyword(effect="you may draw a card", trigger_type="self")

    trigger = kw.create_trigger(gs, perm, perm, to_zone="graveyard")
    assert trigger is not None
    assert trigger.is_optional is True
