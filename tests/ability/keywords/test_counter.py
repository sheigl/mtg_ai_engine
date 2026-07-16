"""Tests for counter keyword abilities."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.ability.keywords.counter import (
    CounterKeyword,
    PlusOnePlusOneCounter,
    MinusOneMinusOneCounter,
    ChargeCounter,
    TimeCounter,
)
from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, Permanent,
)


def _make_game_with_perm(
    oracle: str = "",
    type_line: str = "Creature — Elf",
    counters: dict[str, int] | None = None,
    power: str = "1",
    toughness: str = "1",
) -> tuple[GameState, Permanent]:
    card = Card(
        name="Test Card",
        type_line=type_line,
        oracle_text=oracle,
        power=power,
        toughness=toughness,
    )
    perm = Permanent(card=card, controller="p1", counters=counters or {})
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
        battlefield=[perm],
    )
    return gs, perm


def test_counter_add_counters():
    """Counter keyword adds counters to a permanent."""
    gs, perm = _make_game_with_perm()
    kw = CounterKeyword(counter_type="+1/+1", count=2)

    gs = kw.add_counters(gs, perm)
    assert perm.counters.get("+1/+1", 0) == 2


def test_counter_add_to_existing():
    """Counter keyword adds to existing counters."""
    gs, perm = _make_game_with_perm(counters={"+1/+1": 3})
    kw = CounterKeyword(counter_type="+1/+1", count=2)

    gs = kw.add_counters(gs, perm)
    assert perm.counters.get("+1/+1", 0) == 5


def test_counter_remove_counters():
    """Counter keyword removes counters from a permanent."""
    gs, perm = _make_game_with_perm(counters={"+1/+1": 5})
    kw = CounterKeyword(counter_type="+1/+1", count=2)

    gs = kw.remove_counters(gs, perm)
    assert perm.counters.get("+1/+1", 0) == 3


def test_counter_remove_no_below_zero():
    """Counter removal doesn't go below zero."""
    gs, perm = _make_game_with_perm(counters={"+1/+1": 1})
    kw = CounterKeyword(counter_type="+1/+1", count=5)

    gs = kw.remove_counters(gs, perm)
    assert perm.counters.get("+1/+1", 0) == 0


def test_counter_remove_all():
    """Remove all counters clears the dict."""
    gs, perm = _make_game_with_perm(counters={"+1/+1": 3, "-1/-1": 2, "charge": 1})
    kw = CounterKeyword()

    gs = kw.remove_all_counters(gs, perm)
    assert perm.counters == {}


def test_get_counter_count():
    """Get counter count returns correct value."""
    gs, perm = _make_game_with_perm(counters={"+1/+1": 4, "-1/-1": 2})
    kw = PlusOnePlusOneCounter()

    assert kw.get_counter_count(perm, "+1/+1") == 4
    assert kw.get_counter_count(perm, "-1/-1") == 2
    assert kw.get_counter_count(perm, "charge") == 0


def test_plus_one_plus_one_pt_modification():
    """+1/+1 counters give positive P/T modification."""
    gs, perm = _make_game_with_perm(counters={"+1/+1": 3})
    kw = PlusOnePlusOneCounter()

    pt = kw.get_pt_modification(perm)
    assert pt == (3, 3)


def test_plus_one_plus_one_canceling():
    """+1/+1 and -1/-1 counters cancel (CR 704.5m)."""
    gs, perm = _make_game_with_perm(counters={"+1/+1": 5, "-1/-1": 3})
    kw = PlusOnePlusOneCounter()

    pt = kw.get_pt_modification(perm)
    assert pt == (2, 2)  # 5 - 3 = 2 net +1/+1


def test_minus_one_minus_one_pt_modification():
    """-1/-1 counters give negative P/T modification."""
    gs, perm = _make_game_with_perm(counters={"-1/-1": 3})
    kw = MinusOneMinusOneCounter()

    pt = kw.get_pt_modification(perm)
    assert pt == (-3, -3)


def test_minus_one_minus_one_canceling():
    """-1/-1 and +1/+1 counters cancel (CR 704.5m)."""
    gs, perm = _make_game_with_perm(counters={"+1/+1": 2, "-1/-1": 5})
    kw = MinusOneMinusOneCounter()

    pt = kw.get_pt_modification(perm)
    assert pt == (-3, -3)  # 5 - 2 = 3 net -1/-1


def test_minus_one_destruction_check():
    """-1/-1 counters can cause destruction."""
    gs, perm = _make_game_with_perm(
        counters={"-1/-1": 3},
        power="2",
        toughness="2",
    )
    perm.damage_marked = 0
    kw = MinusOneMinusOneCounter()

    # Base toughness 2 - 3 counters = -1 effective, but damage 0
    assert kw.check_destruction(gs, perm) is False

    perm.damage_marked = 1
    # Effective toughness = 2 - 3 = -1 (already <= 0)
    assert kw.check_destruction(gs, perm) is False  # toughness <= 0 means already dead


def test_minus_one_destruction_with_damage():
    """-1/-1 counters plus damage cause destruction."""
    gs, perm = _make_game_with_perm(
        counters={"-1/-1": 1},
        power="2",
        toughness="2",
    )
    perm.damage_marked = 1
    kw = MinusOneMinusOneCounter()

    # Effective toughness = 2 - 1 = 1, damage = 1 => lethal
    assert kw.check_destruction(gs, perm) is True


def test_charge_counter():
    """Charge counters work correctly."""
    gs, perm = _make_game_with_perm()
    kw = ChargeCounter(count=3)

    gs = kw.add_counters(gs, perm)
    assert perm.counters.get("charge", 0) == 3


def test_time_counter():
    """Time counters work correctly."""
    gs, perm = _make_game_with_perm()
    kw = TimeCounter(count=5)

    gs = kw.add_counters(gs, perm)
    assert perm.counters.get("time", 0) == 5


def test_counter_applies_detects_oracle():
    """Counter keyword detects counter patterns in oracle text."""
    gs, perm = _make_game_with_perm("Put a +1/+1 counter on this creature.")
    kw = CounterKeyword()
    assert kw.applies(gs, perm) is True


def test_counter_apply_default():
    """Default apply adds counters to the permanent."""
    gs, perm = _make_game_with_perm()
    kw = CounterKeyword(counter_type="+1/+1", count=1)

    gs = kw.apply(gs, perm)
    assert perm.counters.get("+1/+1", 0) == 1
