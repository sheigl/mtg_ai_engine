"""
MON-01: The Monarch mechanic tests.
"""
import pytest

from mtg_engine.engine.monarch import set_monarch, handle_end_step_draw, check_combat_damage_monarch
from mtg_engine.models.game import GameState, PlayerState, Card, PendingTrigger


def _make_gs(monarch: str | None = None, active_player: str = "Alice") -> GameState:
    return GameState(
        game_id="test-monarch",
        seed=42,
        turn=1,
        active_player=active_player,
        priority_holder=active_player,
        phase="ending",
        step="end",
        monarch=monarch,
        players=[
            PlayerState(name="Alice", library=[_card(f"A{i}") for i in range(30)]),
            PlayerState(name="Bob", library=[_card(f"B{i}") for i in range(30)]),
        ],
    )


def _card(name: str) -> Card:
    return Card(id=f"id-{name}", name=name, cmc=0.0)


class TestSetMonarch:
    def test_sets_monarch(self):
        gs = _make_gs()
        gs = set_monarch(gs, "Alice")
        assert gs.monarch == "Alice"

    def test_noop_if_already_monarch(self):
        gs = _make_gs(monarch="Alice")
        gs = set_monarch(gs, "Alice")
        assert gs.monarch == "Alice"

    def test_changes_monarch(self):
        gs = _make_gs(monarch="Alice")
        gs = set_monarch(gs, "Bob")
        assert gs.monarch == "Bob"

    def test_fires_become_monarch_trigger(self):
        gs = _make_gs()
        gs = set_monarch(gs, "Alice")
        triggers = [t for t in gs.pending_triggers if t.trigger_type == "become_monarch"]
        assert len(triggers) >= 1
        assert triggers[-1].controller == "Alice"

    def test_no_duplicate_triggers_for_noop(self):
        gs = _make_gs(monarch="Alice")
        before = len(gs.pending_triggers)
        gs = set_monarch(gs, "Alice")
        after = len(gs.pending_triggers)
        assert after == before


class TestEndStepDraw:
    def test_monarch_draws_card(self):
        gs = _make_gs(monarch="Alice")
        alice = gs.players[0]
        hand_before = len(alice.hand)
        gs = handle_end_step_draw(gs)
        assert len(alice.hand) == hand_before + 1

    def test_non_monarch_does_not_draw(self):
        gs = _make_gs(monarch="Bob")
        alice = gs.players[0]
        hand_before = len(alice.hand)
        gs = handle_end_step_draw(gs)
        assert len(alice.hand) == hand_before

    def test_no_monarch_does_nothing(self):
        gs = _make_gs(monarch=None)
        alice = gs.players[0]
        hand_before = len(alice.hand)
        gs = handle_end_step_draw(gs)
        assert len(alice.hand) == hand_before

    def test_active_player_not_monarch_does_not_draw(self):
        gs = _make_gs(monarch="Bob", active_player="Bob")
        bob = gs.players[1]
        hand_before = len(bob.hand)
        gs = handle_end_step_draw(gs)
        assert len(bob.hand) == hand_before + 1  # Bob is active AND monarch

    def test_not_active_player_does_not_draw_even_if_monarch(self):
        gs = _make_gs(monarch="Bob", active_player="Alice")
        bob = gs.players[1]
        hand_before = len(bob.hand)
        gs = handle_end_step_draw(gs)
        assert len(bob.hand) == hand_before  # Alice is active, Bob is monarch, no draw


class TestCombatDamage:
    def test_damage_to_monarch_transfers(self):
        gs = _make_gs(monarch="Bob")
        gs = check_combat_damage_monarch(gs, "Bob", "Alice")
        assert gs.monarch == "Alice"

    def test_damage_to_non_monarch_no_change(self):
        gs = _make_gs(monarch="Bob")
        gs = check_combat_damage_monarch(gs, "Alice", "Charlie")
        assert gs.monarch == "Bob"

    def test_no_monarch_no_change(self):
        gs = _make_gs(monarch=None)
        gs = check_combat_damage_monarch(gs, "Alice", "Bob")
        assert gs.monarch is None

    def test_attacker_already_monarch_noop(self):
        gs = _make_gs(monarch="Alice")
        gs = check_combat_damage_monarch(gs, "Alice", "Alice")
        assert gs.monarch == "Alice"
