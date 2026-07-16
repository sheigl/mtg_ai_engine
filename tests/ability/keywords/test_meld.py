"""Tests for Meld keyword."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.ability.keywords.meld import MeldKeyword
from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, Permanent,
)


def _make_game_with_meld(
    merged_name: str = "Merged Card",
    partner_name: str = "Partner Card",
) -> tuple[GameState, Permanent, PlayerState]:
    oracle = f"Meld — {merged_name}"
    card = Card(
        name="Half Card",
        type_line="Legendary Creature — Human",
        oracle_text=oracle,
        power="3",
        toughness="3",
        card_layout="mdfc",
    )
    perm = Permanent(card=card, controller="p1")
    p1 = PlayerState(name="p1", library=[
        Card(name=partner_name, type_line="Legendary Creature — Human", power="3", toughness="3")
        for _ in range(5)
    ])
    p2 = PlayerState(name="p2")
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
        battlefield=[perm],
    )
    return gs, perm, p1


def test_meld_applies():
    """Meld detects meld in oracle text."""
    gs, perm, _ = _make_game_with_meld()
    kw = MeldKeyword(merged_card_name="Merged Card")
    assert kw.applies(gs, perm) is True


def test_meld_does_not_apply():
    """Meld returns False for non-meld cards."""
    card = Card(
        name="Normal Card",
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
        players=[PlayerState(name="p1")],
    )
    kw = MeldKeyword()
    assert kw.applies(gs, perm) is False


def test_get_merged_card_name():
    """Get merged card name from constructor."""
    kw = MeldKeyword(merged_card_name="My Merged Card")
    card = Card(name="Test", type_line="Creature", oracle_text="")
    perm = Permanent(card=card, controller="p1")
    assert kw.get_merged_card_name(perm) == "My Merged Card"


def test_get_merged_card_name_from_oracle():
    """Get merged card name from oracle text."""
    kw = MeldKeyword()
    card = Card(
        name="Test",
        type_line="Creature",
        oracle_text="Meld — Oracle of the Alpha",
    )
    perm = Permanent(card=card, controller="p1")
    assert kw.get_merged_card_name(perm) == "Oracle of the Alpha"


def test_start_meld():
    """Start meld records the meld state."""
    gs, perm, p1 = _make_game_with_meld()
    kw = MeldKeyword(merged_card_name="Merged", partner_card_name="Partner")

    gs = kw.start_meld(gs, perm, "p1")
    meld_state = getattr(gs, "_meld_in_progress", None)
    assert meld_state is not None
    assert "p1" in meld_state
    assert meld_state["p1"]["merged_card_name"] == "Merged"


def test_start_meld_unknown_player():
    """Start meld does nothing for unknown player."""
    gs, perm, p1 = _make_game_with_meld()
    kw = MeldKeyword(merged_card_name="Merged")

    original_gs = gs
    gs = kw.start_meld(gs, perm, "unknown_player")
    meld_state = getattr(gs, "_meld_in_progress", None)
    assert meld_state is None or "unknown_player" not in meld_state


def test_complete_meld():
    """Complete meld puts merged card on battlefield."""
    gs, perm, p1 = _make_game_with_meld()
    kw = MeldKeyword(merged_card_name="Merged Card", partner_card_name="Partner")

    # Start meld first
    gs = kw.start_meld(gs, perm, "p1")

    # Complete meld
    initial_battlefield_count = len(gs.battlefield)
    gs = kw.complete_meld(gs, "p1")

    # Should have one more permanent (the merged card)
    assert len(gs.battlefield) == initial_battlefield_count + 1
    merged = gs.battlefield[-1]
    assert merged.card.name == "Merged Card"


def test_complete_meld_no_pending():
    """Complete meld does nothing if no meld in progress."""
    gs, perm, p1 = _make_game_with_meld()
    kw = MeldKeyword()

    initial_count = len(gs.battlefield)
    gs = kw.complete_meld(gs, "p1")
    assert len(gs.battlefield) == initial_count


def test_from_oracle():
    """Create MeldKeyword from oracle text."""
    kw = MeldKeyword.from_oracle("Meld — Oracle of the Alpha")
    assert kw is not None
    assert kw.merged_card_name == "Oracle of the Alpha"


def test_from_oracle_missing():
    """from_oracle returns None when not found."""
    assert MeldKeyword.from_oracle("Flying.") is None


def test_meld_description():
    """Meld returns proper description."""
    kw = MeldKeyword(merged_card_name="Oracle of the Alpha")
    desc = kw.get_trigger_description()
    assert "Oracle of the Alpha" in desc
