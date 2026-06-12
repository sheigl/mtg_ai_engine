"""Tests for keyword base class hierarchy."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.ability.keywords.base import (
    PassiveKeyword,
    register_keyword,
    get_keyword,
    create_keyword,
)


def test_keyword_registry_register_and_get():
    """Register and retrieve a keyword class."""
    class TestKeyword(PassiveKeyword):
        name = "test_keyword"

    register_keyword("test_keyword", TestKeyword)
    result = get_keyword("test_keyword")
    assert result is TestKeyword


def test_keyword_registry_case_insensitive():
    """Keyword lookup is case-insensitive."""
    class TestKeyword2(PassiveKeyword):
        name = "test2"

    register_keyword("TEST2", TestKeyword2)
    assert get_keyword("test2") is TestKeyword2
    assert get_keyword("Test2") is TestKeyword2


def test_keyword_registry_missing():
    """Missing keyword returns None."""
    assert get_keyword("nonexistent") is None


def test_create_keyword():
    """Create keyword instance from registry."""
    class SimpleKeyword(PassiveKeyword):
        name = "simple"

    register_keyword("simple", SimpleKeyword)
    kw = create_keyword("simple")
    assert kw is not None
    assert isinstance(kw, SimpleKeyword)


def test_create_keyword_missing():
    """Creating missing keyword returns None."""
    assert create_keyword("nonexistent") is None


def test_passive_keyword_applies():
    """PassiveKeyword checks keyword list."""
    from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState

    card = Card(name="Test", type_line="Creature", keywords=["flying"])
    perm = Permanent(card=card, controller="p1")

    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[PlayerState(name="p1")],
        battlefield=[perm],
    )

    kw = PassiveKeyword()
    kw.name = "flying"
    assert kw.applies(gs, perm) is True

    kw.name = "trample"
    assert kw.applies(gs, perm) is False


def test_passive_keyword_apply_returns_state():
    """PassiveKeyword.apply returns game state unchanged."""
    from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState

    card = Card(name="Test", type_line="Creature", keywords=["flying"])
    perm = Permanent(card=card, controller="p1")

    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[PlayerState(name="p1")],
    )

    kw = PassiveKeyword()
    kw.name = "flying"
    result = kw.apply(gs, perm)
    assert result is gs


def test_matches_keyword():
    """Keyword matches by name."""
    kw = PassiveKeyword()
    kw.name = "Flying"
    assert kw.matches_keyword("flying") is True
    assert kw.matches_keyword("Flying") is True
    assert kw.matches_keyword("trample") is False


def test_get_trigger_description():
    """Default trigger description includes keyword name."""
    kw = PassiveKeyword()
    kw.name = "test"
    assert "test" in kw.get_trigger_description()
