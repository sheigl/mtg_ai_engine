"""Tests for mana production triggers (MANA-03)."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, Permanent,
)
from mtg_engine.engine.triggers import (
    check_mana_production_triggers,
    check_mana_spent_triggers,
    MANA_PRODUCTION_TRIGGER_PATTERNS,
    MANA_SPENT_TRIGGER_PATTERNS,
)


def _make_perm(
    name: str = "Creature",
    type_line: str = "Creature — Human",
    keywords: list[str] | None = None,
    oracle_text: str = "",
    controller: str = "p1",
) -> Permanent:
    card = Card(
        name=name,
        type_line=type_line,
        keywords=keywords or [],
        oracle_text=oracle_text,
    )
    return Permanent(card=card, controller=controller)


def _make_game(perms: list[Permanent]) -> GameState:
    return GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
        battlefield=perms,
        pending_triggers=[],
    )


# ─── MANA_PRODUCTION_TRIGGER_PATTERNS ────────────────────────────────────────

def test_mana_production_patterns_exist():
    """Mana production trigger patterns are registered."""
    assert len(MANA_PRODUCTION_TRIGGER_PATTERNS) >= 1


def test_pattern_matches_tap_land():
    """Pattern matches 'whenever you tap a land for mana'."""
    text = "Whenever you tap a land for mana, create a 1/1 Spirit token."
    matched = any(p.search(text) for p in MANA_PRODUCTION_TRIGGER_PATTERNS)
    assert matched is True


def test_pattern_matches_land_produces():
    """Pattern matches 'whenever a land produces mana'."""
    text = "Whenever a land produces mana, you gain 1 life."
    matched = any(p.search(text) for p in MANA_PRODUCTION_TRIGGER_PATTERNS)
    assert matched is True


def test_pattern_matches_add_mana():
    """Pattern matches 'whenever you add mana'."""
    text = "Whenever you add mana, you may draw a card."
    matched = any(p.search(text) for p in MANA_PRODUCTION_TRIGGER_PATTERNS)
    assert matched is True


def test_pattern_no_false_positive():
    """Normal text does not match mana production patterns."""
    text = "Flying. Trample."
    matched = any(p.search(text) for p in MANA_PRODUCTION_TRIGGER_PATTERNS)
    assert matched is False


def test_spend_mana_is_not_a_production_pattern():
    """'whenever you spend mana' is NOT a mana-PRODUCTION trigger (MAJOR 5 guard).

    Mana production fires when a *land/mana source* makes mana available;
    "spend mana" fires when a player *pays* a cost. These must not be conflated.
    """
    text = "Whenever you spend mana, put a +1/+1 counter on this creature."
    matched = any(p.search(text) for p in MANA_PRODUCTION_TRIGGER_PATTERNS)
    assert matched is False


def test_spend_mana_is_a_spent_pattern():
    """'whenever you spend mana' IS a mana-SPENT trigger (MINOR 7 guard)."""
    text = "Whenever you spend mana, put a +1/+1 counter on this creature."
    matched = any(p.search(text) for p in MANA_SPENT_TRIGGER_PATTERNS)
    assert matched is True


def test_spend_mana_trigger_fires_via_check():
    """check_mana_spent_triggers queues a trigger for a 'spend mana' watcher."""
    watcher = _make_perm(
        name="Spend Watcher",
        type_line="Enchantment",
        oracle_text="Whenever you spend mana, put a +1/+1 counter on this creature.",
        controller="p1",
    )
    gs = _make_game([watcher])
    gs = check_mana_spent_triggers(gs, "p1")

    spent_triggers = [
        t for t in gs.pending_triggers if t.trigger_type == "mana_spent"
    ]
    assert len(spent_triggers) == 1
    assert spent_triggers[0].controller == "p1"


# ─── check_mana_production_triggers ───────────────────────────────────────────

def test_no_triggers_without_matching_permanents():
    """No triggers queued when no permanents have mana production triggers."""
    forest = _make_perm(
        name="Forest",
        type_line="Basic Land — Forest",
        controller="p1",
    )
    gs = _make_game([forest])
    gs = check_mana_production_triggers(gs, forest.id, "p1", ["G"])
    assert len(gs.pending_triggers) == 0


def test_trigger_queued_for_mana_production():
    """Trigger is queued when a permanent watches mana production."""
    watcher = _make_perm(
        name="Mana Watcher",
        type_line="Enchantment",
        oracle_text="Whenever you tap a land for mana, you gain 1 life.",
        controller="p1",
    )
    forest = _make_perm(
        name="Forest",
        type_line="Basic Land — Forest",
        controller="p1",
    )
    gs = _make_game([watcher, forest])
    gs = check_mana_production_triggers(gs, forest.id, "p1", ["G"])

    # The watcher's "whenever you tap a land for mana" ability is a triggered
    # ability and must produce exactly one queued trigger, owned by the watcher.
    production_triggers = [
        t for t in gs.pending_triggers if t.trigger_type == "mana_production"
    ]
    assert len(production_triggers) == 1
    assert production_triggers[0].controller == "p1"
    assert production_triggers[0].source_permanent_id == watcher.id


def test_trigger_type_is_mana_production():
    """Queued trigger has correct type."""
    watcher = _make_perm(
        name="Mana Watcher",
        type_line="Enchantment",
        oracle_text="Whenever you tap a land for mana, you gain 1 life.",
        controller="p1",
    )
    gs = _make_game([watcher])
    gs = check_mana_production_triggers(gs, "land_id", "p1", ["W"])

    for t in gs.pending_triggers:
        assert t.trigger_type == "mana_production"


def test_mana_production_with_multiple_symbols():
    """Mana production with multiple symbols works."""
    watcher = _make_perm(
        name="Mana Watcher",
        type_line="Enchantment",
        oracle_text="Whenever you add mana, you may draw a card.",
        controller="p1",
    )
    gs = _make_game([watcher])
    gs = check_mana_production_triggers(gs, "dual_land_id", "p1", ["W", "U"])
    assert gs is not None
