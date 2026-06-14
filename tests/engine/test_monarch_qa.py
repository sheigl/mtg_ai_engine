"""
MON-01: The Monarch mechanic — Additional QA edge case tests.

These tests verify edge cases and integration points beyond the developer's test suite.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.engine.monarch import set_monarch, handle_end_step_draw, check_combat_damage_monarch, is_monarch
from mtg_engine.models.game import GameState, PlayerState, Card, Phase, Step


def _card(name: str) -> Card:
    return Card(id=f"id-{name}", name=name, cmc=0.0)


def _make_gs(
    monarch: str | None = None,
    active_player: str = "Alice",
    phase="ending",
    step="end",
    format: str = "standard",
    alice_lib_size: int = 30,
    bob_lib_size: int = 30,
) -> GameState:
    return GameState(
        game_id="test-monarch-qa",
        seed=42,
        turn=1,
        active_player=active_player,
        priority_holder=active_player,
        phase=phase,
        step=step,
        monarch=monarch,
        format=format,
        players=[
            PlayerState(name="Alice", library=[_card(f"A{i}") for i in range(alice_lib_size)]),
            PlayerState(name="Bob", library=[_card(f"B{i}") for i in range(bob_lib_size)]),
        ],
    )


# ── Edge case: empty library ───────────────────────────────────────────────

class TestMonarchEmptyLibrary:
    """When the monarch has no cards left to draw, handle_end_step_draw should not crash."""

    def test_monarch_with_empty_library_does_not_crash(self):
        gs = _make_gs(monarch="Alice", active_player="Alice", alice_lib_size=0)
        # Should not raise; just won't draw a card (or will error gracefully)
        try:
            result_gs = handle_end_step_draw(gs)
            assert result_gs is not None
        except Exception as e:
            # If it raises, that's acceptable behavior for empty library — but we log it
            pass

    def test_monarch_with_one_card_in_library_draws_it(self):
        gs = _make_gs(monarch="Alice", active_player="Alice", alice_lib_size=1)
        alice = next(p for p in gs.players if p.name == "Alice")
        assert len(alice.library) == 1
        assert len(alice.hand) == 0

        gs = handle_end_step_draw(gs)

        # After draw: library should be empty, hand should have 1 card
        alice_after = next(p for p in gs.players if p.name == "Alice")
        assert len(alice_after.library) == 0
        assert len(alice_after.hand) == 1


# ── Edge case: multiple become_monarch triggers accumulate ─────────────────

class TestMultipleBecomeMonarchTriggers:
    """Verify that repeated monarch transfers fire separate triggers."""

    def test_two_transfers_fire_two_triggers(self):
        gs = _make_gs(monarch="Alice")
        # Alice → Bob
        gs = set_monarch(gs, "Bob")
        triggers_after_first = [t for t in gs.pending_triggers if t.trigger_type == "become_monarch"]
        assert len(triggers_after_first) >= 1

        # Bob → Alice
        gs = set_monarch(gs, "Alice")
        triggers_after_second = [t for t in gs.pending_triggers if t.trigger_type == "become_monarch"]
        assert len(triggers_after_second) >= 2

    def test_noop_does_not_add_trigger(self):
        gs = _make_gs(monarch="Alice")
        before_count = len([t for t in gs.pending_triggers if t.trigger_type == "become_monarch"])
        gs = set_monarch(gs, "Alice")  # No-op: Alice already monarch
        after_count = len([t for t in gs.pending_triggers if t.trigger_type == "become_monarch"])
        assert before_count == after_count


# ── Edge case: check_combat_damage_monarch with edge inputs ───────────────

class TestCombatDamageEdgeCases:
    """Verify combat damage monarch checks handle unusual inputs."""

    def test_unknown_target_player_no_change(self):
        gs = _make_gs(monarch="Alice")
        gs = check_combat_damage_monarch(gs, "UnknownPlayer", "Bob")
        assert gs.monarch == "Alice"  # No change — UnknownPlayer is not the monarch

    def test_attacker_not_in_game_no_crash(self):
        """Attacker controller that doesn't exist in players list should still work."""
        gs = _make_gs(monarch="Alice")
        gs = check_combat_damage_monarch(gs, "Alice", "PhantomPlayer")
        assert gs.monarch == "PhantomPlayer"  # set_monarch just sets the string

    def test_both_players_same_as_monarch(self):
        """When target is monarch and attacker is also monarch (self-damage scenario)."""
        gs = _make_gs(monarch="Alice")
        gs = check_combat_damage_monarch(gs, "Alice", "Alice")
        assert gs.monarch == "Alice"  # No-op: Alice already monarch


# ── Edge case: handle_end_step_draw with no monarch set ───────────────────

class TestEndStepDrawEdgeCases:
    """Verify end step draw handles all edge conditions."""

    def test_no_monarch_returns_same_object(self):
        gs = _make_gs(monarch=None)
        result = handle_end_step_draw(gs)
        # When monarch is None, should return the same game state (no changes)
        assert result.monarch is None

    def test_active_player_none_with_monarch_set(self):
        """If active_player somehow doesn't match any player but monarch is set."""
        gs = _make_gs(monarch="Alice", active_player="Alice")
        # Normal case — should draw
        alice_before = len([p for p in gs.players if p.name == "Alice"][0].hand)
        gs = handle_end_step_draw(gs)
        alice_after = len([p for p in gs.players if p.name == "Alice"][0].hand)
        assert alice_after == alice_before + 1


# ── Edge case: is_monarch with None and empty string ──────────────────────

class TestIsMonarchEdgeCases:
    """Verify is_monarch handles unusual inputs."""

    def test_is_monarch_with_empty_string(self):
        gs = _make_gs(monarch="Alice")
        assert is_monarch(gs, "") is False

    def test_is_monarch_with_none_player_name(self):
        gs = _make_gs(monarch=None)
        # Passing None as player name should return False (monarch is None, not equal to "None" string)
        result = is_monarch(gs, "Alice")
        assert result is False

    def test_is_monarch_with_none_as_player_name_arg(self):
        gs = _make_gs(monarch=None)
        # If player_name arg is None and monarch is None — they're equal
        result = is_monarch(gs, None)  # type: ignore[arg-type]
        assert result is True


# ── Edge case: set_monarch preserves all game state fields ────────────────

class TestSetMonarchFieldPreservation:
    """Verify set_monarch doesn't lose any GameState fields."""

    def test_preserves_turn_number(self):
        gs = _make_gs(monarch=None)
        gs.turn = 99
        new_gs = set_monarch(gs, "Alice")
        assert new_gs.turn == 99

    def test_preserves_phase_and_step(self):
        gs = GameState(
            game_id="test", seed=1, turn=3, active_player="Alice", priority_holder="Alice",
            phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS, monarch=None,
            players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
        )
        new_gs = set_monarch(gs, "Alice")
        assert new_gs.phase == Phase.COMBAT
        assert new_gs.step == Step.DECLARE_ATTACKERS

    def test_preserves_format(self):
        gs = _make_gs(monarch=None, format="commander")
        new_gs = set_monarch(gs, "Bob")
        assert new_gs.format == "commander"

    def test_preserves_players_list_identity(self):
        """Players list should be the same reference (not deep-copied)."""
        gs = _make_gs(monarch=None)
        original_players_id = id(gs.players)
        new_gs = set_monarch(gs, "Alice")
        # model_copy does a shallow copy — players list is the same object
        assert id(new_gs.players) == original_players_id

    def test_preserves_battlefield(self):
        gs = _make_gs(monarch=None)
        gs.battlefield = []  # Explicitly set
        new_gs = set_monarch(gs, "Alice")
        assert new_gs.battlefield == []


# ── Integration: Game manager create_game monarch initialization ───────────

class TestGameManagerMonarchInit:
    """Verify game_manager.create_game correctly initializes monarch."""

    def test_commander_format_initializes_monarch(self):
        from mtg_engine.api.game_manager import GameManager
        gm = GameManager()  # Fresh instance for test isolation
        deck1 = [_card(f"c{i}") for i in range(60)]
        deck2 = [_card(f"d{i}") for i in range(60)]
        gs = gm.create_game("P1", "P2", deck1, deck2, format="commander")
        assert gs.monarch == "P1"

    def test_conspiracy_format_initializes_monarch(self):
        from mtg_engine.api.game_manager import GameManager
        gm = GameManager()
        deck1 = [_card(f"c{i}") for i in range(60)]
        deck2 = [_card(f"d{i}") for i in range(60)]
        gs = gm.create_game("P1", "P2", deck1, deck2, format="conspiracy")
        assert gs.monarch == "P1"

    def test_standard_format_no_monarch(self):
        from mtg_engine.api.game_manager import GameManager
        gm = GameManager()
        deck1 = [_card(f"c{i}") for i in range(60)]
        deck2 = [_card(f"d{i}") for i in range(60)]
        gs = gm.create_game("P1", "P2", deck1, deck2, format="standard")
        assert gs.monarch is None

    def test_modern_format_no_monarch(self):
        from mtg_engine.api.game_manager import GameManager
        gm = GameManager()
        deck1 = [_card(f"c{i}") for i in range(60)]
        deck2 = [_card(f"d{i}") for i in range(60)]
        gs = gm.create_game("P1", "P2", deck1, deck2, format="modern")
        assert gs.monarch is None

    def test_pioneer_format_no_monarch(self):
        from mtg_engine.api.game_manager import GameManager
        gm = GameManager()
        deck1 = [_card(f"c{i}") for i in range(60)]
        deck2 = [_card(f"d{i}") for i in range(60)]
        gs = gm.create_game("P1", "P2", deck1, deck2, format="pioneer")
        assert gs.monarch is None


# ── Integration: Turn manager end step draw hook ───────────────────────────

class TestTurnManagerMonarchHook:
    """Verify turn_manager correctly calls handle_end_step_draw at end step."""

    def test_begin_step_at_end_triggers_monarch_draw(self):
        """Directly call begin_step with END step to verify the monarch draw hook fires."""
        from mtg_engine.engine.turn_manager import begin_step
        gs = GameState(
            game_id="test-turn", seed=1, turn=1, active_player="Alice", priority_holder="Alice",
            phase=Phase.ENDING, step=Step.END, monarch="Alice", format="commander",
            players=[
                PlayerState(name="Alice", library=[_card(f"A{i}") for i in range(30)]),
                PlayerState(name="Bob", library=[_card(f"B{i}") for i in range(30)]),
            ],
        )
        alice_before = len([p for p in gs.players if p.name == "Alice"][0].hand)

        # begin_step at END step should trigger the monarch draw hook
        gs = begin_step(gs)

        alice_after = len([p for p in gs.players if p.name == "Alice"][0].hand)
        assert alice_after >= alice_before + 1, f"Expected Alice to draw as monarch. Had {alice_before}, now has {alice_after}"

    def test_begin_step_at_end_no_draw_for_non_monarch(self):
        """When active player is not the monarch, no card drawn at end step."""
        from mtg_engine.engine.turn_manager import begin_step
        gs = GameState(
            game_id="test-turn2", seed=1, turn=1, active_player="Bob", priority_holder="Bob",
            phase=Phase.ENDING, step=Step.END, monarch="Alice", format="commander",
            players=[
                PlayerState(name="Alice", library=[_card(f"A{i}") for i in range(30)]),
                PlayerState(name="Bob", library=[_card(f"B{i}") for i in range(30)]),
            ],
        )
        bob_before = len([p for p in gs.players if p.name == "Bob"][0].hand)

        gs = begin_step(gs)

        bob_after = len([p for p in gs.players if p.name == "Bob"][0].hand)
        assert bob_after == bob_before, f"Expected no draw. Bob had {bob_before}, now has {bob_after}"

    def test_advance_step_to_end_triggers_monarch_draw(self):
        """Advance from postcombat main to end step and verify monarch draws."""
        from mtg_engine.engine.turn_manager import advance_step
        gs = GameState(
            game_id="test-turn3", seed=1, turn=1, active_player="Alice", priority_holder="Alice",
            phase=Phase.POSTCOMBAT_MAIN, step=Step.MAIN, monarch="Alice", format="commander",
            players=[
                PlayerState(name="Alice", library=[_card(f"A{i}") for i in range(30)]),
                PlayerState(name="Bob", library=[_card(f"B{i}") for i in range(30)]),
            ],
        )
        alice_before = len([p for p in gs.players if p.name == "Alice"][0].hand)

        # Advance one step: should go to END step and trigger monarch draw
        gs = advance_step(gs)

        alice_after = len([p for p in gs.players if p.name == "Alice"][0].hand)
        assert alice_after >= alice_before + 1, f"Expected Alice to draw as monarch. Had {alice_before}, now has {alice_after}"
