"""
PRO-01: Proliferate system tests.
"""
import pytest

from mtg_engine.engine.proliferate import (
    get_proliferate_eligible,
    apply_proliferate,
    setup_pending_proliferate,
)
from mtg_engine.models.game import GameState, PlayerState, Permanent, Card


def _make_gs_with_counters(
    perm_counters: dict[str, int] | None = None,
    poison: int = 0,
) -> GameState:
    card = Card(name="Test Creature", type_line="Creature", power="2", toughness="2")
    perm = Permanent(
        id="perm-1",
        card=card,
        controller="Alice",
        counters=perm_counters or {},
    )
    return GameState(
        game_id="test-pro",
        seed=42,
        turn=1,
        active_player="Alice",
        priority_holder="Alice",
        players=[
            PlayerState(name="Alice", life=20, poison_counters=poison),
            PlayerState(name="Bob", life=20),
        ],
        battlefield=[perm],
    )


class TestGetProliferateEligible:
    def test_no_counters_nothing_eligible(self):
        gs = _make_gs_with_counters()
        eligible = get_proliferate_eligible(gs)
        assert eligible == []

    def test_plus_one_counter_eligible(self):
        gs = _make_gs_with_counters({"+1/+1": 2})
        eligible = get_proliferate_eligible(gs)
        assert len(eligible) == 1
        assert eligible[0]["id"] == "perm-1"
        assert eligible[0]["counters"] == {"+1/+1": 2}

    def test_internal_counters_not_counted(self):
        gs = _make_gs_with_counters({"__deathtouch_damage__": 5})
        eligible = get_proliferate_eligible(gs)
        assert eligible == []

    def test_poison_counters_eligible(self):
        gs = _make_gs_with_counters(poison=3)
        eligible = get_proliferate_eligible(gs)
        assert len(eligible) == 1
        assert eligible[0]["id"] == "Alice"

    def test_multiple_counters_on_one_permanent(self):
        gs = _make_gs_with_counters({"+1/+1": 1, "lore": 2})
        eligible = get_proliferate_eligible(gs)
        assert len(eligible) == 1
        assert eligible[0]["counters"] == {"+1/+1": 1, "lore": 2}

    def test_no_poison_no_player_eligible(self):
        gs = _make_gs_with_counters(poison=0)
        eligible = get_proliferate_eligible(gs)
        assert eligible == []

    def test_permanent_and_player_both_eligible(self):
        gs = _make_gs_with_counters({"+1/+1": 1}, poison=2)
        eligible = get_proliferate_eligible(gs)
        assert len(eligible) == 2


class TestApplyProliferate:
    def test_adds_one_counter(self):
        gs = _make_gs_with_counters({"+1/+1": 2})
        gs = apply_proliferate(gs, ["perm-1"])
        perm = gs.battlefield[0]
        assert perm.counters["+1/+1"] == 3

    def test_multiple_counter_types_all_increment(self):
        gs = _make_gs_with_counters({"+1/+1": 1, "lore": 3})
        gs = apply_proliferate(gs, ["perm-1"])
        perm = gs.battlefield[0]
        assert perm.counters["+1/+1"] == 2
        assert perm.counters["lore"] == 4

    def test_poison_counter_increments(self):
        gs = _make_gs_with_counters(poison=2)
        gs = apply_proliferate(gs, ["Alice"])
        assert gs.players[0].poison_counters == 3

    def test_multiple_targets(self):
        card2 = Card(name="Second", type_line="Creature", power="1", toughness="1")
        perm2 = Permanent(id="perm-2", card=card2, controller="Alice",
                          counters={"charge": 1})
        gs = _make_gs_with_counters({"+1/+1": 1}, poison=1)
        gs.battlefield.append(perm2)
        gs = apply_proliferate(gs, ["perm-1", "perm-2", "Alice"])
        assert gs.battlefield[0].counters["+1/+1"] == 2
        assert gs.battlefield[1].counters["charge"] == 2
        assert gs.players[0].poison_counters == 2

    def test_noop_for_invalid_target(self):
        gs = _make_gs_with_counters({"+1/+1": 1})
        gs = apply_proliferate(gs, ["nonexistent"])
        assert gs.battlefield[0].counters["+1/+1"] == 1

    def test_internal_counters_skipped(self):
        gs = _make_gs_with_counters({"+1/+1": 1, "__hidden__": 99})
        gs = apply_proliferate(gs, ["perm-1"])
        perm = gs.battlefield[0]
        assert perm.counters["+1/+1"] == 2
        assert perm.counters.get("__hidden__") == 99  # unchanged


class TestSetupPendingProliferate:
    def test_sets_choice_on_state(self):
        gs = _make_gs_with_counters({"+1/+1": 1})
        gs = setup_pending_proliferate(gs, "Alice")
        assert gs.pending_proliferate_choice is not None
        assert gs.pending_proliferate_choice["player"] == "Alice"
        assert len(gs.pending_proliferate_choice["eligible"]) == 1
