"""
DNG-01 Integration Tests: Day/Night Cycle through full turn flow.

Tests day/night transitions via begin_step(), _advance_turn(), permanent
transform immutability, complete cycles, explicit set immutability, and trigger
firing behavior.
"""
import pytest
from mtg_engine.models.game import (
    GameState, PlayerState, Card, Phase, Step, CardFace, Permanent,
)
from mtg_engine.engine.turn_manager import begin_step, _advance_turn
from mtg_engine.engine.daynight import check_daynight_transition, set_day, set_night, is_daytime


def _make_game(is_day=None, spells_last=0) -> GameState:
    p1 = PlayerState(name="p1", library=[Card(name=f"C{i}") for i in range(20)])
    p2 = PlayerState(name="p2", library=[Card(name=f"C{i}") for i in range(20)])
    return GameState(
        game_id="test-dng-integration", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.BEGINNING, step=Step.UNTAP,
        players=[p1, p2],
        is_day=is_day,
        spells_cast_last_turn=spells_last,
    )


class TestDayNightViaTurnManager:
    """Test day/night transitions through the full turn_manager flow."""

    def test_untap_triggers_day_to_night(self):
        """When it's day and prev player cast 0 spells, untap triggers night transition."""
        gs = _make_game(is_day=True, spells_last=0)
        new_gs = begin_step(gs)
        assert is_daytime(new_gs) is False

    def test_untap_triggers_night_to_day(self):
        """When it's night and prev player cast 2+ spells, untap triggers day transition."""
        gs = _make_game(is_day=False, spells_last=3)
        new_gs = begin_step(gs)
        assert is_daytime(new_gs) is True

    def test_untap_no_transition_when_neither(self):
        """When is_day=None, no transition occurs during untap."""
        gs = _make_game(is_day=None, spells_last=0)
        new_gs = begin_step(gs)
        assert is_daytime(new_gs) is None

    def test_advance_turn_snapshots_spell_count(self):
        """_advance_turn captures previous player's spell count for day/night."""
        gs = _make_game(is_day=True, spells_last=0)
        gs.spells_cast_this_turn_by_player["p1"] = 3

        new_gs = _advance_turn(gs)

        # Snapshot should capture p1's count (prev active player)
        assert new_gs.spells_cast_last_turn == 3
        # Counters reset for new turn
        assert new_gs.spells_cast_this_turn == 0
        assert new_gs.spells_cast_this_turn_by_player == {}

    def test_advance_turn_does_not_mutate_original(self):
        """_advance_turn returns new GameState, original unchanged."""
        gs = _make_game(is_day=True)
        gs.spells_cast_this_turn = 5

        old_id = id(gs)
        new_gs = _advance_turn(gs)

        assert id(new_gs) != old_id
        assert gs.spells_cast_this_turn == 5  # Original unchanged


class TestPermanentTransformImmutability:
    """Test that daybound transforms don't mutate original permanents."""

    def test_transform_creates_new_permanent(self):
        """Daybound permanent gets a new object with flipped face_index."""
        card = Card(
            name="Daybound Wolf", type_line="Creature — Werewolf",
            oracle_text="Daybound (If a player casts no spells during their turn, it becomes night.)",
        )
        card.faces = [
            CardFace(name="Wolf", type_line="Creature", oracle_text=""),
            CardFace(name="Werewolf", type_line="Creature", oracle_text=""),
        ]
        perm = Permanent(id="perm_1", card=card, controller="p1", face_index=0)

        gs = _make_game(is_day=True, spells_last=0)
        gs.battlefield = [perm]

        new_gs = begin_step(gs)  # Goes through untap → check_daynight_transition

        assert perm.face_index == 0  # Original unchanged
        assert new_gs.battlefield[0].face_index == 1  # New object flipped
        assert id(new_gs.battlefield[0]) != id(perm)

    def test_non_daybound_permanent_unchanged(self):
        """Regular permanents are not affected by day/night transition."""
        card = Card(name="Grizzly Bears", type_line="Creature — Bear")
        perm = Permanent(id="perm_1", card=card, controller="p1", face_index=0)

        gs = _make_game(is_day=True, spells_last=0)
        gs.battlefield = [perm]

        new_gs = check_daynight_transition(gs)  # Direct call, no untap interference

        # Same object reference (no transform needed for non-daybound)
        assert new_gs.battlefield[0] is perm


class TestFullDayNightCycle:
    """Test complete day→night→day cycle across turns."""

    def test_day_to_night_cycle(self):
        """Day → Night when 0 spells cast, then stays night until 2+ spells."""
        gs = _make_game(is_day=True, spells_last=0)

        # Turn 1: Day → Night (prev player cast 0)
        gs = begin_step(gs)
        assert is_daytime(gs) is False

        # Simulate p1 casting 0 spells on their turn (p1 is active during this turn)
        gs.spells_cast_this_turn_by_player["p1"] = 0
        gs = _advance_turn(gs)

        # Turn 2: Night stays night (prev player p1 cast 0, need 2+)
        gs = begin_step(gs)
        assert is_daytime(gs) is False

    def test_night_to_day_cycle(self):
        """Night → Day when 2+ spells cast."""
        gs = _make_game(is_day=False, spells_last=3)

        # Turn 1: Night → Day (prev player cast 3)
        gs = begin_step(gs)
        assert is_daytime(gs) is True

        # Simulate p1 casting 0 spells on their turn (p1 is active during this turn)
        gs.spells_cast_this_turn_by_player["p1"] = 0
        gs = _advance_turn(gs)

        # Turn 2: Day → Night (prev player p1 cast 0)
        gs = begin_step(gs)
        assert is_daytime(gs) is False

    def test_full_round_trip(self):
        """Day → Night → Day → Night across multiple turns."""
        gs = _make_game(is_day=True, spells_last=0)

        # Day → Night (0 spells)
        gs = begin_step(gs)
        assert is_daytime(gs) is False

        # Cast 3 spells this turn (p1 is active player during p1's turn)
        gs.spells_cast_this_turn_by_player["p1"] = 3
        gs = _advance_turn(gs)

        # Night → Day (3 spells from prev active player p1)
        gs = begin_step(gs)
        assert is_daytime(gs) is True

        # Cast 0 spells this turn (p2 is now active after advance_turn)
        gs.spells_cast_this_turn_by_player["p2"] = 0
        gs = _advance_turn(gs)

        # Day → Night again (0 spells from prev active player p2)
        gs = begin_step(gs)
        assert is_daytime(gs) is False


class TestSetExplicitImmutability:
    """Test that set_day/set_night don't mutate original state."""

    def test_set_day_returns_new_state(self):
        gs = _make_game(is_day=None)
        new_gs = set_day(gs)

        assert id(new_gs) != id(gs)
        assert is_daytime(gs) is None  # Original unchanged
        assert is_daytime(new_gs) is True

    def test_set_night_returns_new_state(self):
        gs = _make_game(is_day=None)
        new_gs = set_night(gs)

        assert id(new_gs) != id(gs)
        assert is_daytime(gs) is None  # Original unchanged
        assert is_daytime(new_gs) is False


class TestTriggerFiring:
    """Test that day/night transitions occur correctly without dead system triggers."""

    def test_transition_changes_is_day_not_pending_triggers(self):
        """check_daynight_transition changes is_day but does not add system-level triggers."""
        gs = _make_game(is_day=True, spells_last=0)
        original_triggers = list(gs.pending_triggers)  # Copy

        new_gs = check_daynight_transition(gs)

        # Transition happened
        assert is_daytime(new_gs) is False
        # Original triggers list unchanged
        assert len(gs.pending_triggers) == len(original_triggers)
        # No system-level trigger added (card ability triggers handled by turn_manager wiring)
        assert len(new_gs.pending_triggers) == len(original_triggers)

    def test_untap_chain_performs_transition(self):
        """Full untap flow (begin_step) performs the day/night transition."""
        gs = _make_game(is_day=True, spells_last=0)

        new_gs = begin_step(gs)

        # Transition happened via is_day change
        assert is_daytime(new_gs) is False


class TestUntapImmutability:
    """Test that begin_step(UNTAP) doesn't mutate original state."""

    def test_untap_does_not_mutate_permanents(self):
        """Active player's permanents are untapped via model_copy, not mutation."""
        card = Card(name="Grizzly Bears", type_line="Creature — Bear")
        perm = Permanent(
            id="perm_1", card=card, controller="p1",
            tapped=True, summoning_sick=True, loyalty_activated_this_turn=True,
        )

        gs = _make_game(is_day=None)  # No day/night to simplify
        gs.battlefield = [perm]

        new_gs = begin_step(gs)

        # Original permanent unchanged
        assert perm.tapped is True
        assert perm.summoning_sick is True
        assert perm.loyalty_activated_this_turn is True
        # New battlefield has untapped version
        new_perm = new_gs.battlefield[0]
        assert new_perm.tapped is False
        assert new_perm.summoning_sick is False
        assert new_perm.loyalty_activated_this_turn is False

    def test_untap_does_not_mutate_player(self):
        """Active player's lands_played_this_turn reset via model_copy."""
        gs = _make_game(is_day=None)
        # Set initial value
        active = next(p for p in gs.players if p.name == "p1")
        assert active.lands_played_this_turn == 0

        new_gs = begin_step(gs)

        # Original player state unchanged (same object reference since no change needed)
        original_active = next(p for p in gs.players if p.name == "p1")
        assert original_active.lands_played_this_turn == 0


class TestExtraTurnsImmutability:
    """Test that _advance_turn handles extra_turns without mutation."""

    def test_extra_turn_preserves_remaining(self):
        """extra_turns list is not mutated when popping for next turn."""
        gs = _make_game(is_day=True)
        gs.extra_turns = ["p1", "p2"]  # p2 on top (LIFO)

        old_extra_id = id(gs.extra_turns)
        new_gs = _advance_turn(gs)

        # Original extra_turns list unchanged
        assert len(gs.extra_turns) == 2
        assert gs.extra_turns == ["p1", "p2"]
        # New state has remaining turns (p2 popped, p1 remains)
        assert new_gs.extra_turns == ["p1"]

    def test_extra_turn_new_list_object(self):
        """extra_turns in new GameState is a different list object."""
        gs = _make_game(is_day=True)
        gs.extra_turns = ["p3"]

        new_gs = _advance_turn(gs)

        assert id(new_gs.extra_turns) != id(gs.extra_turns)
        assert new_gs.extra_turns == []


class TestMixedBattlefield:
    """Test battlefield with both daybound and regular permanents."""

    def test_mixed_battlefield_transform(self):
        """Only daybound permanents get new objects; others keep references."""
        # Daybound card
        dnc = Card(
            name="Daybound Wolf", type_line="Creature — Werewolf",
            oracle_text="Daybound (If a player casts no spells during their turn, it becomes night.)",
        )
        dnc.faces = [
            CardFace(name="Wolf", type_line="Creature", oracle_text=""),
            CardFace(name="Werewolf", type_line="Creature", oracle_text=""),
        ]
        day_perm = Permanent(id="perm_day", card=dnc, controller="p1", face_index=0)

        # Regular card
        reg_card = Card(name="Grizzly Bears", type_line="Creature — Bear")
        reg_perm = Permanent(id="perm_reg", card=reg_card, controller="p1", face_index=0)

        gs = _make_game(is_day=True, spells_last=0)
        gs.battlefield = [day_perm, reg_perm]

        new_gs = check_daynight_transition(gs)  # Direct call to isolate transform logic

        # Daybound: new object with flipped face
        assert id(new_gs.battlefield[0]) != id(day_perm)
        assert new_gs.battlefield[0].face_index == 1
        assert day_perm.face_index == 0  # Original unchanged

        # Regular: same object reference (no transform needed for non-daybound)
        assert new_gs.battlefield[1] is reg_perm


class TestNightToDayTransform:
    """Test that night→day also transforms permanents correctly."""

    def test_night_to_day_flips_face_back(self):
        """When transitioning night→day, face_index flips from 1 back to 0."""
        card = Card(
            name="Daybound Wolf", type_line="Creature — Werewolf",
            oracle_text="Nightbound (If a player casts two or more spells during their turn, it becomes day.)",
        )
        card.faces = [
            CardFace(name="Wolf", type_line="Creature", oracle_text=""),
            CardFace(name="Werewolf", type_line="Creature", oracle_text=""),
        ]
        perm = Permanent(id="perm_1", card=card, controller="p1", face_index=1)

        gs = _make_game(is_day=False, spells_last=3)
        gs.battlefield = [perm]

        new_gs = begin_step(gs)  # Night → Day transition

        assert perm.face_index == 1  # Original unchanged
        assert new_gs.battlefield[0].face_index == 0  # Flipped back to day face
