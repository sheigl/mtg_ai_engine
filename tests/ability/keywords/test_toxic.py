"""Tests for Toxic keyword."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.ability.keywords.toxic import ToxicKeyword
from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, Permanent,
)


def _make_game_with_toxic(
    toxic_value: int = 2,
    keywords: list[str] | None = None,
) -> tuple[GameState, Permanent, PlayerState]:
    oracle = f"Toxic {toxic_value}"
    card = Card(
        name="Toxic Creature",
        type_line="Creature — Spider",
        oracle_text=oracle,
        power="2",
        toughness="2",
        keywords=keywords or [f"toxic {toxic_value}"],
    )
    perm = Permanent(card=card, controller="p1")
    p1 = PlayerState(name="p1")
    p2 = PlayerState(name="p2", poison_counters=0)
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
        battlefield=[perm],
    )
    return gs, perm, p2


def test_toxic_applies_from_keywords():
    """Toxic detects keyword in keywords list."""
    gs, perm, _ = _make_game_with_toxic(keywords=["toxic 2"])
    kw = ToxicKeyword(value=2)
    assert kw.applies(gs, perm) is True


def test_toxic_applies_from_oracle():
    """Toxic detects keyword in oracle text."""
    gs, perm, _ = _make_game_with_toxic(keywords=[])
    kw = ToxicKeyword(value=2)
    assert kw.applies(gs, perm) is True


def test_toxic_does_not_apply():
    """Toxic returns False for non-toxic creatures."""
    card = Card(
        name="Normal Creature",
        type_line="Creature — Bear",
        oracle_text="Vigilance.",
        power="3",
        toughness="3",
    )
    perm = Permanent(card=card, controller="p1")
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
    )
    kw = ToxicKeyword()
    assert kw.applies(gs, perm) is False


def test_get_toxic_value_from_oracle():
    """Toxic value is parsed from oracle text."""
    gs, perm, _ = _make_game_with_toxic(toxic_value=5)
    kw = ToxicKeyword(value=1)  # Default is overridden by oracle
    assert kw.get_toxic_value(perm) == 5


def test_get_toxic_value_default():
    """Toxic value falls back to constructor value."""
    gs, perm, _ = _make_game_with_toxic(toxic_value=3)
    kw = ToxicKeyword(value=3)
    assert kw.get_toxic_value(perm) == 3


def test_apply_toxic_gives_poison_counters():
    """Toxic gives poison counters to damaged player."""
    gs, perm, p2 = _make_game_with_toxic(toxic_value=3)
    kw = ToxicKeyword(value=3)

    assert p2.poison_counters == 0
    gs = kw.apply_toxic(gs, perm, "p2")
    assert p2.poison_counters == 3


def test_apply_toxic_independent_of_damage_amount():
    """Toxic gives fixed counters regardless of damage amount."""
    gs, perm, p2 = _make_game_with_toxic(toxic_value=2)
    kw = ToxicKeyword(value=2)

    gs = kw.apply_toxic(gs, perm, "p2")
    assert p2.poison_counters == 2  # Not based on damage, just toxic value


def test_apply_toxic_accumulates():
    """Toxic poison counters accumulate."""
    gs, perm, p2 = _make_game_with_toxic(toxic_value=4)
    p2.poison_counters = 3
    kw = ToxicKeyword(value=4)

    gs = kw.apply_toxic(gs, perm, "p2")
    assert p2.poison_counters == 7


def test_apply_toxic_lethal_poison():
    """Toxic tracks lethal poison threshold (10+)."""
    gs, perm, p2 = _make_game_with_toxic(toxic_value=1)
    p2.poison_counters = 9
    kw = ToxicKeyword(value=1)

    gs = kw.apply_toxic(gs, perm, "p2")
    assert p2.poison_counters == 10


def test_from_oracle():
    """Create ToxicKeyword from oracle text."""
    kw = ToxicKeyword.from_oracle("Toxic 5")
    assert kw is not None
    assert kw.value == 5


def test_from_oracle_missing():
    """from_oracle returns None when not found."""
    assert ToxicKeyword.from_oracle("Flying. Trample.") is None


def test_toxic_description():
    """Toxic returns proper description."""
    kw = ToxicKeyword(value=3)
    desc = kw.get_trigger_description()
    assert "Toxic 3" in desc
    assert "3 poison counters" in desc
