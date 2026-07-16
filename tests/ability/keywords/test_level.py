"""Tests for Level Up keyword."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.ability.keywords.level import LevelUpKeyword, parse_level_up
from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, Permanent,
)


def _make_game_with_perm(
    oracle: str = "",
    counters: dict[str, int] | None = None,
) -> tuple[GameState, Permanent]:
    card = Card(
        name="Test Card",
        type_line="Creature — Human",
        oracle_text=oracle,
        power="1",
        toughness="1",
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


def test_level_up_applies():
    """Level Up detects level up in oracle text."""
    oracle = "Level up {2}{G} — Put two +1/+1 counters on this creature.\nLevel 2 — Flying."
    gs, perm = _make_game_with_perm(oracle)
    kw = LevelUpKeyword(cost="{2}{G}", effect="Put two +1/+1 counters on this creature.")
    assert kw.applies(gs, perm) is True


def test_level_up_does_not_apply():
    """Level Up returns False for cards without level up."""
    gs, perm = _make_game_with_perm("Flying.")
    kw = LevelUpKeyword()
    assert kw.applies(gs, perm) is False


def test_get_level_no_counters():
    """Level is 0 with no level counters."""
    gs, perm = _make_game_with_perm()
    kw = LevelUpKeyword()
    assert kw.get_level(perm) == 0


def test_get_level_with_counters():
    """Level equals number of level counters."""
    gs, perm = _make_game_with_perm(counters={"level": 4})
    kw = LevelUpKeyword()
    assert kw.get_level(perm) == 4


def test_level_up_action():
    """Level up adds level counters."""
    oracle = "Level up {2}{G} — Put two +1/+1 counters on this creature."
    gs, perm = _make_game_with_perm(oracle)
    kw = LevelUpKeyword(cost="{2}{G}", effect="Put two +1/+1 counters on this creature.")

    gs = kw.level_up(gs, perm)
    assert perm.counters.get("level", 0) == 2


def test_level_up_action_default_counters():
    """Level up defaults to 2 counters when effect doesn't specify."""
    gs, perm = _make_game_with_perm("Level up {3} — Do something.")
    kw = LevelUpKeyword(cost="{3}", effect="Do something.")

    gs = kw.level_up(gs, perm)
    assert perm.counters.get("level", 0) == 2


def test_level_up_one_counter():
    """Level up parses 'put a +1/+1 counter' as 1."""
    gs, perm = _make_game_with_perm("Level up {G} — Put a +1/+1 counter on this creature.")
    kw = LevelUpKeyword(cost="{G}", effect="Put a +1/+1 counter on this creature.")

    gs = kw.level_up(gs, perm)
    assert perm.counters.get("level", 0) == 1


def test_get_active_abilities():
    """Active abilities include all levels met or exceeded."""
    gs, perm = _make_game_with_perm(counters={"level": 3})
    kw = LevelUpKeyword(
        level_abilities=[
            (2, "Flying"),
            (4, "Trample"),
            (6, "Haste"),
        ]
    )

    active = kw.get_active_abilities(perm)
    assert active == ["Flying"]


def test_get_active_abilities_multiple():
    """Multiple level abilities activate at higher levels."""
    gs, perm = _make_game_with_perm(counters={"level": 5})
    kw = LevelUpKeyword(
        level_abilities=[
            (2, "Flying"),
            (4, "Trample"),
            (6, "Haste"),
        ]
    )

    active = kw.get_active_abilities(perm)
    assert active == ["Flying", "Trample"]


def test_parse_level_up():
    """Parse Level Up from oracle text."""
    oracle = (
        "Level up {2}{G} — Put two +1/+1 counters on this creature.\n"
        "Level 2 — Flying.\n"
        "Level 4 — Trample."
    )
    kw = parse_level_up(oracle)
    assert kw is not None
    assert kw.cost == "{2}{G}"
    assert len(kw.level_abilities) == 2
    assert kw.level_abilities[0] == (2, "Flying.")
    assert kw.level_abilities[1] == (4, "Trample.")


def test_parse_level_up_missing():
    """Parse returns None when no Level Up found."""
    assert parse_level_up("Flying. Trample.") is None


def test_level_up_description():
    """Level Up returns proper description."""
    kw = LevelUpKeyword(cost="{2}{G}", effect="Put two counters")
    desc = kw.get_trigger_description()
    assert "{2}{G}" in desc
    assert "Put two counters" in desc
