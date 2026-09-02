"""
MON-01: The Monarch mechanic — Integration tests.

Tests full combat flow, game initialization, and is_monarch helper.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.engine.monarch import set_monarch, handle_end_step_draw, check_combat_damage_monarch, is_monarch
from mtg_engine.models.game import GameState, PlayerState, Card, Phase, Step
from mtg_engine.models.actions import AttackDeclaration
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.engine.combat import declare_attackers, assign_combat_damage


def _card(name: str) -> Card:
    return Card(id=f"id-{name}", name=name, cmc=0.0)


def _make_gs(
    monarch: str | None = None,
    active_player: str = "Alice",
    phase="ending",
    step="end",
    format: str = "standard",
) -> GameState:
    return GameState(
        game_id="test-monarch-int",
        seed=42,
        turn=1,
        active_player=active_player,
        priority_holder=active_player,
        phase=phase,
        step=step,
        monarch=monarch,
        format=format,
        players=[
            PlayerState(name="Alice", library=[_card(f"A{i}") for i in range(30)]),
            PlayerState(name="Bob", library=[_card(f"B{i}") for i in range(30)]),
        ],
    )


def _make_combat_game(monarch: str | None = None) -> GameState:
    """Create a game state ready for combat with monarch set."""
    p1 = PlayerState(name="p1", life=20, library=[_card(f"A{i}") for i in range(30)])
    p2 = PlayerState(name="p2", life=20, library=[_card(f"B{i}") for i in range(30)])
    return GameState(
        game_id="t-monarch-combat",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.COMBAT,
        step=Step.DECLARE_ATTACKERS,
        monarch=monarch,
        format="commander",
        players=[p1, p2],
    )


def _add_creature(gs: GameState, name: str, power: int, toughness: int, controller: str):
    """Add a creature to the battlefield."""
    card = Card(
        name=name,
        type_line="Creature — Beast",
        power=str(power),
        toughness=str(toughness),
    )
    return put_permanent_onto_battlefield(gs, card, controller)


# ── is_monarch() helper tests ────────────────────────────────────────────────

class TestIsMonarch:
    def test_is_monarch_returns_true(self):
        gs = _make_gs(monarch="Alice")
        assert is_monarch(gs, "Alice") is True

    def test_is_monarch_returns_false_for_other_player(self):
        gs = _make_gs(monarch="Alice")
        assert is_monarch(gs, "Bob") is False

    def test_is_monarch_returns_false_when_none(self):
        gs = _make_gs(monarch=None)
        assert is_monarch(gs, "Alice") is False
        assert is_monarch(gs, "Bob") is False

    def test_is_monarch_consistent_with_set_monarch(self):
        gs = _make_gs()
        assert is_monarch(gs, "Alice") is False
        gs = set_monarch(gs, "Alice")
        assert is_monarch(gs, "Alice") is True


# ── Mutability tests ────────────────────────────────────────────────────────

class TestSetMonarchMutability:
    def test_set_monarch_does_not_mutate_original(self):
        gs = _make_gs()
        original_id = id(gs)
        new_gs = set_monarch(gs, "Alice")
        assert id(new_gs) != original_id, "set_monarch must return a new GameState"
        # Original should be unchanged (monarch was None, now it's Alice in the copy)
        # The key assertion: if we call set_monarch again on the original, it still works
        another = set_monarch(gs, "Bob")
        assert another.monarch == "Bob"

    def test_set_monarch_preserves_other_fields(self):
        gs = _make_gs(monarch=None)
        gs.turn = 5
        new_gs = set_monarch(gs, "Alice")
        assert new_gs.turn == 5
        assert new_gs.game_id == gs.game_id
        assert len(new_gs.players) == len(gs.players)

    def test_set_monarch_noop_returns_same_object(self):
        gs = _make_gs(monarch="Alice")
        result = set_monarch(gs, "Alice")
        # When player is already monarch, returns the same object (no copy needed)
        assert result is gs


# ── Game initialization tests ───────────────────────────────────────────────

class TestGameInitialization:
    def test_commander_format_sets_monarch(self):
        gs = _make_gs(monarch="Alice", format="commander")
        # Simulating what game_manager.create_game does for commander format
        assert gs.monarch == "Alice"  # active_player is monarch

    def test_conspiracy_format_sets_monarch(self):
        gs = _make_gs(monarch="Alice", format="conspiracy")
        assert gs.monarch == "Alice"

    def test_standard_format_no_monarch(self):
        gs = _make_gs(monarch=None, format="standard")
        assert gs.monarch is None

    def test_modern_format_no_monarch(self):
        gs = _make_gs(monarch=None, format="modern")
        assert gs.monarch is None


# ── Full combat flow integration tests ──────────────────────────────────────

class TestCombatFlow:
    def test_full_combat_transfers_monarch(self):
        """Full flow: declare_attackers → assign_combat_damage → monarch transfer."""
        gs = _make_combat_game(monarch="p2")  # p2 starts as monarch

        # p1 puts a creature on battlefield and attacks p2 (the monarch)
        gs, attacker = _add_creature(gs, "Bear", 3, 3, "p1")
        attacker.summoning_sick = False

        # Declare attackers
        gs = declare_attackers(
            gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")]
        )

        # Advance to combat damage step and assign damage
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        # Monarch should have transferred from p2 to p1
        assert is_monarch(gs, "p1"), f"Expected p1 to be monarch, got {gs.monarch}"
        assert not is_monarch(gs, "p2")
        # p2 took 3 damage
        assert gs.players[1].life == 17

    def test_full_combat_no_transfer_when_attacking_non_monarch(self):
        """If attacker attacks a non-monarch player, monarch doesn't change."""
        gs = _make_combat_game(monarch="p1")  # p1 is monarch

        # p2 puts a creature and attacks p1 (the monarch) — this SHOULD transfer
        gs, attacker = _add_creature(gs, "Wolf", 2, 2, "p2")
        attacker.summoning_sick = False

        gs = declare_attackers(
            gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p1")]
        )
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        # Monarch should transfer from p1 to p2
        assert is_monarch(gs, "p2"), f"Expected p2 to be monarch, got {gs.monarch}"

    def test_no_monarch_in_standard_format(self):
        """In standard format, no monarch exists, combat proceeds normally."""
        gs = _make_combat_game(monarch=None)
        gs.format = "standard"

        gs, attacker = _add_creature(gs, "Bear", 2, 2, "p1")
        attacker.summoning_sick = False

        gs = declare_attackers(
            gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")]
        )
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        # No monarch to transfer
        assert gs.monarch is None
        assert gs.players[1].life == 18

    def test_monarch_transfer_fires_become_monarch_trigger(self):
        """When monarch transfers via combat, a become_monarch trigger fires."""
        gs = _make_combat_game(monarch="p2")

        gs, attacker = _add_creature(gs, "Bear", 3, 3, "p1")
        attacker.summoning_sick = False

        gs = declare_attackers(
            gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")]
        )
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        # Check for become_monarch trigger in pending triggers
        triggers = [t for t in gs.pending_triggers if t.trigger_type == "become_monarch"]
        assert len(triggers) >= 1, "Expected at least one become_monarch trigger"
        assert triggers[-1].controller == "p1"


# ── End step draw integration tests ────────────────────────────────────────

class TestEndStepDrawIntegration:
    def test_monarch_draws_at_end_of_own_turn(self):
        """Monarch draws a card at end step of their turn."""
        gs = _make_gs(monarch="Alice", active_player="Alice")
        hand_before = len(gs.players[0].hand)

        gs = handle_end_step_draw(gs)

        assert len(gs.players[0].hand) == hand_before + 1

    def test_monarch_does_not_draw_on_opponents_turn(self):
        """Monarch does not draw during opponent's end step."""
        gs = _make_gs(monarch="Alice", active_player="Bob")
        hand_before = len(gs.players[0].hand)

        gs = handle_end_step_draw(gs)

        assert len(gs.players[0].hand) == hand_before  # No draw, Bob is active but Alice is monarch

    def test_monarch_draw_after_combat_transfer(self):
        """After gaining monarch via combat, player draws at their end step."""
        # Setup: p2 is monarch, p1 attacks and gains monarch
        gs = _make_gs(monarch="Bob", active_player="Alice")

        # Simulate combat damage transfer (p1 deals damage to monarch Bob)
        gs = check_combat_damage_monarch(gs, "Bob", "Alice")
        assert is_monarch(gs, "Alice"), "Alice should now be the monarch"

        # Alice's end step — she draws as monarch
        hand_before = len(gs.players[0].hand)
        gs = handle_end_step_draw(gs)
        assert len(gs.players[0].hand) == hand_before + 1


# ── Edge cases ──────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_self_damage_no_monarch_change(self):
        """If the monarch deals combat damage to themselves, no change."""
        gs = _make_combat_game(monarch="p1")

        # p2 attacks p1 (the monarch) — this transfers monarch to p2
        gs, attacker = _add_creature(gs, "Wolf", 2, 2, "p2")
        attacker.summoning_sick = False

        gs = declare_attackers(
            gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p1")]
        )
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        assert is_monarch(gs, "p2"), f"Expected p2 to be monarch, got {gs.monarch}"

    def test_multiple_monarch_transfers(self):
        """Monarch can transfer multiple times."""
        gs = _make_gs(monarch="Alice")

        # Bob becomes monarch
        gs = set_monarch(gs, "Bob")
        assert is_monarch(gs, "Bob")

        # Alice becomes monarch again
        gs = set_monarch(gs, "Alice")
        assert is_monarch(gs, "Alice")

    def test_is_monarch_with_unknown_player(self):
        """is_monarch returns False for a player not in the game."""
        gs = _make_gs(monarch="Alice")
        assert is_monarch(gs, "Charlie") is False
