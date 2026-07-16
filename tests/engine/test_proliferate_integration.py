"""
PRO-01: Proliferate integration tests.

Covers full proliferate flow: card effect → pending choice → resolution → trigger firing,
AI auto-resolution, pure transforms, internal counter exclusion, poison counters, etc.
"""
import pytest

from mtg_engine.engine.proliferate import (
    apply_proliferate,
    setup_pending_proliferate,
    get_proliferate_eligible,
    _resolve_proliferate_with_ai,
)
from mtg_engine.engine.stack import _apply_single_effect_text
from mtg_engine.engine.triggers import check_proliferated_triggers
from mtg_engine.models.game import GameState, PlayerState, Card, Permanent, StackObject


def _make_game() -> GameState:
    """Create a game state with counters for testing."""
    card = Card(name="Test Creature", type_line="Creature — Beast", power="2", toughness="2")
    perm = Permanent(
        id="perm-1", card=card, controller="Alice", counters={"charge": 3},
    )
    return GameState(
        game_id="test-pro-integ", seed=42, turn=1,
        active_player="Alice", priority_holder="Alice",
        players=[
            PlayerState(name="Alice", life=20, poison_counters=2,
                        library=[Card(name=f"C{i}") for i in range(20)]),
            PlayerState(name="Bob", life=20, poison_counters=1),
        ],
        battlefield=[perm],
    )


class TestPureTransforms:
    """Test that proliferate functions return new GameState objects."""

    def test_apply_proliferate_returns_new_state(self):
        gs = _make_game()
        old_id = id(gs)
        gs = apply_proliferate(gs, ["perm-1"])
        assert id(gs) != old_id

    def test_setup_pending_returns_new_state(self):
        gs = _make_game()
        old_id = id(gs)
        gs = setup_pending_proliferate(gs, "Alice")
        assert id(gs) != old_id

    def test_apply_proliferate_does_not_mutate_original(self):
        """Original GameState battlefield is unchanged after apply."""
        gs = _make_game()
        original_counters = dict(gs.battlefield[0].counters)
        new_gs = apply_proliferate(gs, ["perm-1"])
        # Original permanent counters should be untouched
        assert gs.battlefield[0].counters == original_counters

    def test_apply_proliferate_does_not_mutate_original_player(self):
        """Original player poison_counters is unchanged after apply."""
        gs = _make_game()
        original_poison = gs.players[0].poison_counters
        new_gs = apply_proliferate(gs, ["Alice"])
        assert gs.players[0].poison_counters == original_poison

    def test_check_proliferated_triggers_returns_new_state(self):
        """check_proliferated_triggers returns a new GameState."""
        flux = Permanent(
            id="flux-1",
            card=Card(name="Flux Channeler", type_line="Creature — Elemental",
                      oracle_text="Whenever you proliferate, draw a card.",
                      power="2", toughness="2"),
            controller="Alice",
        )
        gs = _make_game()
        gs.battlefield.append(flux)
        old_id = id(gs)
        new_gs = check_proliferated_triggers(gs, "Alice")
        assert id(new_gs) != old_id


class TestStackIntegration:
    """Test that card effects trigger proliferate via stack resolution."""

    def test_human_player_gets_pending_choice(self):
        """Human player casting a proliferate spell gets pending choice."""
        gs = _make_game()
        gs.human_player_name = "Alice"

        stack_obj = StackObject(
            source_card=Card(name="Test Card", oracle_text="Proliferate."),
            controller="Alice",
        )
        gs = _apply_single_effect_text(gs, stack_obj, "Proliferate.")

        assert gs.pending_proliferate_choice is not None
        assert gs.pending_proliferate_choice["player"] == "Alice"

    def test_ai_player_auto_resolves(self):
        """AI player casting a proliferate spell auto-resolves."""
        gs = _make_game()
        gs.human_player_name = None  # AI

        stack_obj = StackObject(
            source_card=Card(name="Test Card", oracle_text="Proliferate."),
            controller="Alice",
        )
        gs = _apply_single_effect_text(gs, stack_obj, "Proliferate.")

        assert gs.pending_proliferate_choice is None  # Auto-resolved
        # Alice's perm should have gained a counter
        perm = next(p for p in gs.battlefield if p.id == "perm-1")
        assert perm.counters["charge"] == 4

    def test_ai_player_does_not_help_opponents(self):
        """AI proliferate only targets own permanents, not opponent's."""
        card2 = Card(name="Opponent Creature", type_line="Creature — Beast", power="1", toughness="1")
        opp_perm = Permanent(
            id="perm-opp", card=card2, controller="Bob", counters={"+1/+1": 5},
        )
        gs = _make_game()
        gs.battlefield.append(opp_perm)
        gs.human_player_name = None

        stack_obj = StackObject(
            source_card=Card(name="Test Card", oracle_text="Proliferate."),
            controller="Alice",
        )
        gs = _apply_single_effect_text(gs, stack_obj, "Proliferate.")

        # Alice's perm should have gained counter
        alice_perm = next(p for p in gs.battlefield if p.id == "perm-1")
        assert alice_perm.counters["charge"] == 4
        # Bob's perm should NOT have changed (AI doesn't help opponents)
        bob_perm = next(p for p in gs.battlefield if p.id == "perm-opp")
        assert bob_perm.counters["+1/+1"] == 5


class TestTriggerFiring:
    """Test that 'whenever you proliferate' triggers fire after resolution."""

    def test_proliferated_trigger_fires(self):
        flux = Permanent(
            id="flux-1",
            card=Card(name="Flux Channeler", type_line="Creature — Elemental",
                      oracle_text="Whenever you proliferate, draw a card.",
                      power="2", toughness="2"),
            controller="Alice",
        )
        gs = _make_game()
        gs.battlefield.append(flux)

        gs = apply_proliferate(gs, ["perm-1"])
        gs = check_proliferated_triggers(gs, "Alice")

        prolif_triggers = [t for t in gs.pending_triggers if t.trigger_type == "proliferated"]
        assert len(prolif_triggers) >= 1

    def test_trigger_not_fired_for_other_player(self):
        """Flux Channeler only triggers when its controller proliferates."""
        flux = Permanent(
            id="flux-1",
            card=Card(name="Flux Channeler", type_line="Creature — Elemental",
                      oracle_text="Whenever you proliferate, draw a card.",
                      power="2", toughness="2"),
            controller="Bob",  # Controlled by Bob
        )
        gs = _make_game()
        gs.battlefield.append(flux)

        gs = apply_proliferate(gs, ["perm-1"])
        gs = check_proliferated_triggers(gs, "Alice")  # Alice proliferates

        # Flux Channeler is controlled by Bob; "you" = Bob, not Alice
        # Trigger should NOT fire because Alice (not Bob) proliferated
        prolif_triggers = [t for t in gs.pending_triggers if t.trigger_type == "proliferated"]
        assert len(prolif_triggers) == 0


class TestInternalCounterExclusion:
    """Test that internal engine counters are not eligible."""

    def test_internal_counters_not_eligible(self):
        perm = Permanent(
            id="perm-int",
            card=Card(name="Deathtouch Creature", type_line="Creature — Zombie",
                      power="2", toughness="2"),
            controller="Alice",
            counters={"__deathtouch_damage__": 5},
        )
        gs = _make_game()
        gs.battlefield.append(perm)

        eligible = get_proliferate_eligible(gs)
        eligible_ids = [e["id"] for e in eligible]
        assert "perm-int" not in eligible_ids

    def test_mixed_counters_only_real_ones_counted(self):
        """Perm with both real and internal counters: only real ones proliferate."""
        perm = Permanent(
            id="perm-mix",
            card=Card(name="Mixed Creature", type_line="Creature — Zombie",
                      power="2", toughness="2"),
            controller="Alice",
            counters={"+1/+1": 3, "__deathtouch_damage__": 5},
        )
        # Use game without poison counters to isolate perm eligibility
        gs = GameState(
            game_id="test-pro-integ", seed=42, turn=1,
            active_player="Alice", priority_holder="Alice",
            players=[
                PlayerState(name="Alice", life=20),
                PlayerState(name="Bob", life=20),
            ],
        )
        gs.battlefield.append(perm)

        eligible = get_proliferate_eligible(gs)
        assert len(eligible) == 1
        assert eligible[0]["id"] == "perm-mix"
        assert "+1/+1" in eligible[0]["counters"]
        assert "__deathtouch_damage__" not in eligible[0]["counters"]

    def test_internal_counters_preserved_after_proliferate(self):
        """Internal counters remain unchanged after proliferate."""
        perm = Permanent(
            id="perm-mix",
            card=Card(name="Mixed Creature", type_line="Creature — Zombie",
                      power="2", toughness="2"),
            controller="Alice",
            counters={"+1/+1": 3, "__deathtouch_damage__": 5},
        )
        gs = _make_game()
        gs.battlefield.clear()
        gs.battlefield.append(perm)

        gs = apply_proliferate(gs, ["perm-mix"])
        new_perm = next(p for p in gs.battlefield if p.id == "perm-mix")
        assert new_perm.counters["+1/+1"] == 4
        assert new_perm.counters["__deathtouch_damage__"] == 5


class TestMultipleCounterTypes:
    """Test that all counter types on a permanent increment."""

    def test_all_counter_types_increment(self):
        perm = Permanent(
            id="multi",
            card=Card(name="Multi Counter", type_line="Creature — Beast",
                      power="2", toughness="2"),
            controller="Alice",
            counters={"charge": 3, "+1/+1": 1, "lore": 2},
        )
        gs = _make_game()
        gs.battlefield.append(perm)

        gs = apply_proliferate(gs, ["multi"])
        multi_perm = next(p for p in gs.battlefield if p.id == "multi")
        assert multi_perm.counters["charge"] == 4
        assert multi_perm.counters["+1/+1"] == 2
        assert multi_perm.counters["lore"] == 3


class TestPoisonCounterProliferation:
    """Test poison counter proliferation on players."""

    def test_poison_counter_increments(self):
        gs = _make_game()
        gs = apply_proliferate(gs, ["Alice"])

        alice = next(p for p in gs.players if p.name == "Alice")
        assert alice.poison_counters == 3  # Was 2, now 3

    def test_poison_counter_increments_for_other_player(self):
        """Simulate API handler calling apply_proliferate with opponent target."""
        gs = _make_game()
        gs = apply_proliferate(gs, ["Bob"])

        bob = next(p for p in gs.players if p.name == "Bob")
        assert bob.poison_counters == 2  # Was 1, now 2

    def test_no_poison_counter_not_eligible(self):
        """Player with 0 poison counters is not eligible."""
        card = Card(name="Test", type_line="Creature", power="1", toughness="1")
        perm = Permanent(id="p", card=card, controller="Alice")
        gs = GameState(
            game_id="test-no-poison", seed=1, turn=1,
            active_player="Alice", priority_holder="Alice",
            players=[
                PlayerState(name="Alice", life=20),  # No poison
                PlayerState(name="Bob", life=20),
            ],
            battlefield=[perm],
        )
        eligible = get_proliferate_eligible(gs)
        player_ids = [e["id"] for e in eligible if e["type"] == "player"]
        assert "Alice" not in player_ids


class TestAIHeuristic:
    """Test AI auto-resolution heuristic."""

    def test_ai_proliferates_to_own_targets_only(self):
        gs = _make_game()
        old_id = id(gs)
        gs = _resolve_proliferate_with_ai(gs, "Alice")

        assert id(gs) != old_id  # Pure transform
        # Alice's perm should have gained counter
        alice_perm = next(p for p in gs.battlefield if p.id == "perm-1")
        assert alice_perm.counters["charge"] == 4
        # Alice herself (poison) should also be proliferated
        alice_player = next(p for p in gs.players if p.name == "Alice")
        assert alice_player.poison_counters == 3

    def test_ai_does_not_proliferate_to_opponent(self):
        """AI never helps opponent's permanents."""
        card2 = Card(name="Opponent", type_line="Creature — Beast", power="1", toughness="1")
        opp_perm = Permanent(
            id="perm-opp", card=card2, controller="Bob", counters={"+1/+1": 5},
        )
        gs = _make_game()
        gs.battlefield.append(opp_perm)

        gs = _resolve_proliferate_with_ai(gs, "Alice")

        # Bob's perm should NOT have changed
        bob_perm = next(p for p in gs.battlefield if p.id == "perm-opp")
        assert bob_perm.counters["+1/+1"] == 5


class TestEmptyTargets:
    """Test edge cases with no eligible targets."""

    def test_no_eligible_targets_is_safe(self):
        gs = GameState(
            game_id="test-empty", seed=1, turn=1,
            active_player="Alice", priority_holder="Alice",
            players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
            battlefield=[],
        )
        eligible = get_proliferate_eligible(gs)
        assert eligible == []

    def test_apply_empty_targets_is_noop(self):
        gs = _make_game()
        old_id = id(gs)
        gs2 = apply_proliferate(gs, [])
        # Empty targets returns same state (no-op optimization)
        assert gs2 is gs or id(gs2) == old_id

    def test_setup_pending_with_no_eligible(self):
        """Setup pending proliferate with no eligible targets still works."""
        gs = GameState(
            game_id="test-empty", seed=1, turn=1,
            active_player="Alice", priority_holder="Alice",
            players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
            battlefield=[],
        )
        gs = setup_pending_proliferate(gs, "Alice")
        assert gs.pending_proliferate_choice is not None
        assert gs.pending_proliferate_choice["eligible"] == []

    def test_ai_resolves_with_no_targets(self):
        """AI auto-resolve with no eligible targets is safe."""
        gs = GameState(
            game_id="test-empty", seed=1, turn=1,
            active_player="Alice", priority_holder="Alice",
            players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
            battlefield=[],
        )
        new_gs = _resolve_proliferate_with_ai(gs, "Alice")
        assert new_gs is not None


class TestFullFlow:
    """Test the complete proliferate flow from card effect to resolution."""

    def test_full_human_flow(self):
        """Card effect → pending choice → apply → triggers fire."""
        gs = _make_game()
        gs.human_player_name = "Alice"

        # Step 1: Card effect triggers proliferate
        stack_obj = StackObject(
            source_card=Card(name="Test Card", oracle_text="Proliferate."),
            controller="Alice",
        )
        gs = _apply_single_effect_text(gs, stack_obj, "Proliferate.")

        # Step 2: Verify pending choice is set
        assert gs.pending_proliferate_choice is not None
        eligible_ids = [e["id"] for e in gs.pending_proliferate_choice["eligible"]]
        assert "perm-1" in eligible_ids
        assert "Alice" in eligible_ids

        # Step 3: Apply proliferate (simulating API handler)
        gs = apply_proliferate(gs, ["perm-1", "Alice"])

        # Step 4: Verify counters incremented
        perm = next(p for p in gs.battlefield if p.id == "perm-1")
        assert perm.counters["charge"] == 4
        alice = next(p for p in gs.players if p.name == "Alice")
        assert alice.poison_counters == 3

    def test_full_ai_flow(self):
        """Card effect → AI auto-resolve (no pending choice)."""
        gs = _make_game()
        gs.human_player_name = None  # AI game

        stack_obj = StackObject(
            source_card=Card(name="Test Card", oracle_text="Proliferate."),
            controller="Alice",
        )
        gs = _apply_single_effect_text(gs, stack_obj, "Proliferate.")

        # No pending choice — AI auto-resolved
        assert gs.pending_proliferate_choice is None

        # Alice's targets should have been proliferated
        perm = next(p for p in gs.battlefield if p.id == "perm-1")
        assert perm.counters["charge"] == 4
        alice = next(p for p in gs.players if p.name == "Alice")
        assert alice.poison_counters == 3
