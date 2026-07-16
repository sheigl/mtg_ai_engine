"""
DNG-01: Day/Night Cycle tests.
"""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, PendingTrigger
from mtg_engine.engine.daynight import (
    check_daynight_transition,
    set_day,
    set_night,
    is_daytime,
)


def _make_card(name: str, mana_cost: str = "{0}", type_line: str = "Creature",
               oracle_text: str = "") -> Card:
    return Card(name=name, mana_cost=mana_cost, type_line=type_line,
                oracle_text=oracle_text)


def _gs(is_day=None, prev_casts: int = 0) -> GameState:
    p1 = PlayerState(name="p1", library=[])
    p2 = PlayerState(name="p2", library=[])
    return GameState(
        game_id="test-dng", seed=1,
        active_player="p1",
        priority_holder="p1",
        players=[p1, p2],
        is_day=is_day,
        spells_cast_last_turn=prev_casts,
    )


class TestDayNightTransitions:
    def test_initially_neither(self):
        gs = _gs()
        assert is_daytime(gs) is None

    def test_day_to_night_when_zero_spells(self):
        gs = _gs(is_day=True, prev_casts=0)
        gs = check_daynight_transition(gs)
        assert is_daytime(gs) is False

    def test_day_stays_day_when_spells_cast(self):
        gs = _gs(is_day=True, prev_casts=1)
        gs = check_daynight_transition(gs)
        assert is_daytime(gs) is True

    def test_night_to_day_when_two_plus_spells(self):
        gs = _gs(is_day=False, prev_casts=2)
        gs = check_daynight_transition(gs)
        assert is_daytime(gs) is True

    def test_night_to_day_when_three_spells(self):
        gs = _gs(is_day=False, prev_casts=3)
        gs = check_daynight_transition(gs)
        assert is_daytime(gs) is True

    def test_night_stays_night_when_few_spells(self):
        gs = _gs(is_day=False, prev_casts=1)
        gs = check_daynight_transition(gs)
        assert is_daytime(gs) is False

    def test_night_stays_night_when_zero_spells(self):
        gs = _gs(is_day=False, prev_casts=0)
        gs = check_daynight_transition(gs)
        assert is_daytime(gs) is False

    def test_no_transition_when_no_daynight(self):
        """When is_day is None, transition has no effect."""
        gs = _gs(is_day=None, prev_casts=0)
        triggers_before = len(gs.pending_triggers)
        gs = check_daynight_transition(gs)
        assert is_daytime(gs) is None
        assert len(gs.pending_triggers) == triggers_before

    def test_day_to_night_adds_trigger(self):
        gs = _gs(is_day=True, prev_casts=0)
        gs = check_daynight_transition(gs)
        assert any("day_to_night" in t.trigger_type for t in gs.pending_triggers)

    def test_night_to_day_adds_trigger(self):
        gs = _gs(is_day=False, prev_casts=2)
        new_gs = check_daynight_transition(gs)
        assert any("night_to_day" in t.trigger_type for t in new_gs.pending_triggers)

    def test_no_transition_returns_same_object(self):
        """When no transition occurs, the same GameState object is returned."""
        gs = _gs(is_day=True, prev_casts=1)
        result = check_daynight_transition(gs)
        assert result is gs  # Same object when no change needed


class TestSetExplicit:
    def test_set_day(self):
        gs = _gs(is_day=None)
        new_gs = set_day(gs)
        assert is_daytime(new_gs) is True

    def test_set_day_adds_trigger(self):
        gs = _gs(is_day=None)
        new_gs = set_day(gs)
        assert any("set_to_day" in t.trigger_type for t in new_gs.pending_triggers)

    def test_set_night(self):
        gs = _gs(is_day=None)
        new_gs = set_night(gs)
        assert is_daytime(new_gs) is False

    def test_set_night_adds_trigger(self):
        gs = _gs(is_day=None)
        new_gs = set_night(gs)
        assert any("set_to_night" in t.trigger_type for t in new_gs.pending_triggers)

    def test_set_day_does_not_mutate_original(self):
        """set_day returns a new GameState, original unchanged."""
        gs = _gs(is_day=None)
        triggers_before = len(gs.pending_triggers)
        new_gs = set_day(gs)

        assert id(new_gs) != id(gs)
        assert is_daytime(gs) is None  # Original unchanged
        assert len(gs.pending_triggers) == triggers_before  # Original triggers list unchanged

    def test_set_night_does_not_mutate_original(self):
        """set_night returns a new GameState, original unchanged."""
        gs = _gs(is_day=None)
        triggers_before = len(gs.pending_triggers)
        new_gs = set_night(gs)

        assert id(new_gs) != id(gs)
        assert is_daytime(gs) is None  # Original unchanged
        assert len(gs.pending_triggers) == triggers_before  # Original triggers list unchanged


class TestDayboundTransform:
    def test_daybound_creature_transforms_on_transition(self):
        """When transitioning day→night, daybound permanents flip to nightbound face."""
        from mtg_engine.models.game import CardFace, Permanent
        card = _make_card(
            "Daybound Creature",
            type_line="Creature — Werewolf",
            oracle_text="Daybound (If a player casts no spells during their turn, it becomes night.)",
        )
        card.faces = [
            CardFace(name="Day Face", type_line="Creature", oracle_text="Day side"),
            CardFace(name="Night Face", type_line="Creature", oracle_text="Night side"),
        ]
        perm = Permanent(id="perm_1", card=card, controller="p1", face_index=0)

        gs = _gs(is_day=True, prev_casts=0)
        gs.battlefield = [perm]

        new_gs = check_daynight_transition(gs)

        # Original permanent unchanged (immutability)
        assert perm.face_index == 0
        # New battlefield has a different permanent object with flipped face
        new_perm = new_gs.battlefield[0]
        assert id(new_perm) != id(perm)
        assert new_perm.face_index == 1  # flipped to night face

    def test_day_to_night_does_not_mutate_original(self):
        """check_daynight_transition returns a new GameState, original unchanged."""
        gs = _gs(is_day=True, prev_casts=0)
        original_id = id(gs)
        original_is_day = gs.is_day

        new_gs = check_daynight_transition(gs)

        assert id(new_gs) != original_id
        assert gs.is_day is original_is_day  # Still True on original

    def test_no_transform_without_daybound(self):
        """Regular creatures don't transform on day/night transition."""
        card = _make_card("Grizzly Bears", mana_cost="{1}{G}")
        from mtg_engine.models.game import Permanent
        perm = Permanent(id="perm_1", card=card, controller="p1", face_index=0)

        gs = _gs(is_day=True, prev_casts=0)
        gs.battlefield = [perm]

        new_gs = check_daynight_transition(gs)

        assert perm.face_index == 0  # unchanged
        # Non-daybound permanents are the same object reference (no copy needed)
        assert new_gs.battlefield[0] is perm


class TestSpellTracking:
    def test_spells_cast_this_turn_tracked(self):
        """Test that spells_cast_this_turn and per-player dict are tracked."""
        gs = _gs()
        gs.spells_cast_this_turn += 1
        gs.spells_cast_this_turn_by_player["p1"] = \
            gs.spells_cast_this_turn_by_player.get("p1", 0) + 1
        assert gs.spells_cast_this_turn == 1
        assert gs.spells_cast_this_turn_by_player.get("p1") == 1

    def test_per_player_isolation(self):
        gs = _gs()
        gs.spells_cast_this_turn_by_player["p1"] = 3
        gs.spells_cast_this_turn_by_player["p2"] = 2
        assert gs.spells_cast_this_turn_by_player == {"p1": 3, "p2": 2}
