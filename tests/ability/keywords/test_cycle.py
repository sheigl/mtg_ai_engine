"""Tests for TypeCycling keyword."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.ability.keywords.cycle import TypeCyclingKeyword
from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card,
)


def _make_game_with_card(
    type_line: str = "Creature — Elf Warrior",
    keywords: list[str] | None = None,
    library_size: int = 10,
) -> tuple[GameState, Card, PlayerState]:
    card = Card(
        name="Cycling Card",
        type_line=type_line,
        oracle_text="Type cycling {2}",
        keywords=keywords or ["typecycling"],
    )
    p1 = PlayerState(
        name="p1",
        hand=[card],
        library=[Card(name=f"Card{i}", type_line="Basic Land — Forest") for i in range(library_size)],
    )
    p2 = PlayerState(name="p2")
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
    )
    return gs, card, p1


def test_typecycling_applies_from_keywords():
    """TypeCycling detects keyword in keywords list."""
    gs, card, _ = _make_game_with_card(keywords=["typecycling"])
    perm_card = Card(
        name="Cycling Card",
        type_line="Creature",
        oracle_text="Type cycling {2}",
        keywords=["typecycling"],
    )
    from mtg_engine.models.game import Permanent
    perm = Permanent(card=perm_card, controller="p1")
    gs.battlefield = [perm]

    kw = TypeCyclingKeyword()
    assert kw.applies(gs, perm) is True


def test_typecycling_applies_from_oracle():
    """TypeCycling detects keyword in oracle text."""
    perm_card = Card(
        name="Cycling Card",
        type_line="Creature",
        oracle_text="Type cycling {2}",
        keywords=[],
    )
    from mtg_engine.models.game import Permanent
    perm = Permanent(card=perm_card, controller="p1")
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[PlayerState(name="p1")],
        battlefield=[perm],
    )
    kw = TypeCyclingKeyword()
    assert kw.applies(gs, perm) is True


def test_typecycling_does_not_apply():
    """TypeCycling returns False for non-cycling cards."""
    perm_card = Card(
        name="Normal Card",
        type_line="Creature",
        oracle_text="Flying.",
        keywords=["flying"],
    )
    from mtg_engine.models.game import Permanent
    perm = Permanent(card=perm_card, controller="p1")
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[PlayerState(name="p1")],
    )
    kw = TypeCyclingKeyword()
    assert kw.applies(gs, perm) is False


def test_get_card_type_count_simple():
    """Count types for simple type line."""
    card = Card(name="Test", type_line="Creature")
    kw = TypeCyclingKeyword()
    assert kw.get_card_type_count(card) == 1


def test_get_card_type_count_with_subtype():
    """Count types with subtypes."""
    card = Card(name="Test", type_line="Creature — Elf Warrior")
    kw = TypeCyclingKeyword()
    # "Creature" + "Elf" + "Warrior" = 3
    assert kw.get_card_type_count(card) == 3


def test_get_card_type_count_legendary():
    """Count types with supertype."""
    card = Card(name="Test", type_line="Legendary Creature — Human Wizard")
    kw = TypeCyclingKeyword()
    # "Legendary" + "Creature" + "Human" + "Wizard" = 4
    assert kw.get_card_type_count(card) == 4


def test_get_draw_count():
    """Draw count equals type count."""
    card = Card(name="Test", type_line="Creature — Elf Warrior")
    kw = TypeCyclingKeyword()
    assert kw.get_draw_count(card) == 3


def test_type_cycle_discards_and_draws():
    """Type cycling discards the card and draws cards."""
    gs, card, p1 = _make_game_with_card(type_line="Creature — Elf Warrior")
    kw = TypeCyclingKeyword()

    assert card in p1.hand
    assert len(p1.hand) == 1
    assert len(p1.library) == 10

    gs = kw.type_cycle(gs, card, "p1")

    assert card not in p1.hand
    assert card in p1.graveyard
    assert len(p1.hand) == 3  # Drew 3 cards
    assert len(p1.library) == 7  # 10 - 3 = 7


def test_type_cycle_minimum_one():
    """Type cycling draws at least 1 card."""
    gs, card, p1 = _make_game_with_card(type_line="Creature")
    kw = TypeCyclingKeyword()

    gs = kw.type_cycle(gs, card, "p1")
    assert len(p1.hand) == 1  # Drew 1 card


def test_type_cycle_empty_library():
    """Type cycling handles empty library gracefully."""
    gs, card, p1 = _make_game_with_card(type_line="Creature — Elf", library_size=0)
    kw = TypeCyclingKeyword()

    gs = kw.type_cycle(gs, card, "p1")
    assert card not in p1.hand
    assert card in p1.graveyard
    # Hand should have 0 cards since library is empty
    assert len(p1.hand) == 0


def test_from_oracle():
    """Create TypeCyclingKeyword from oracle text."""
    kw = TypeCyclingKeyword.from_oracle("Type cycling {2}")
    assert kw is not None
    assert kw.base_cost == "{2}"


def test_from_oracle_missing():
    """from_oracle returns None when not found."""
    assert TypeCyclingKeyword.from_oracle("Flying.") is None


def test_typecycling_description():
    """TypeCycling returns proper description."""
    kw = TypeCyclingKeyword(base_cost="{2}")
    desc = kw.get_trigger_description()
    assert "{2}" in desc
    assert "types" in desc
