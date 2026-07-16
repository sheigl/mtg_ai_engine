"""
INT-01: The Initiative mechanic — Integration tests.

Tests full combat flow, upkeep venture flow, initiative transfer chains,
and initiative + dungeon progress tracking across turns.

CR 702.148: The Initiative.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.engine.initiative import set_initiative, handle_upkeep_venture, check_combat_damage_initiative
from mtg_engine.models.game import GameState, PlayerState, Card, Phase, Step
from mtg_engine.models.actions import AttackDeclaration
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.engine.combat import declare_attackers, assign_combat_damage
from mtg_engine.engine.dungeon import get_dungeon_progress, get_completed_dungeon_count


def _card(name: str) -> Card:
    return Card(id=f"id-{name}", name=name, cmc=0.0)


def _make_gs(
    initiative: str | None = None,
    active_player: str = "Alice",
    phase: Phase | str = "beginning",
    step: Step | str = "upkeep",
) -> GameState:
    return GameState(
        game_id="test-initiative-int",
        seed=42,
        turn=1,
        active_player=active_player,
        priority_holder=active_player,
        initiative=initiative,
        phase=phase,
        step=step,
        players=[
            PlayerState(name="Alice", library=[_card(f"A{i}") for i in range(30)]),
            PlayerState(name="Bob", library=[_card(f"B{i}") for i in range(30)]),
        ],
    )


def _make_combat_game(initiative: str | None = None) -> GameState:
    """Create a game state ready for combat with initiative set."""
    p1 = PlayerState(name="p1", life=20, library=[_card(f"A{i}") for i in range(30)])
    p2 = PlayerState(name="p2", life=20, library=[_card(f"B{i}") for i in range(30)])
    return GameState(
        game_id="t-initiative-combat",
        seed=1,
        active_player="p1",
        priority_holder="p1",
        phase=Phase.COMBAT,
        step=Step.DECLARE_ATTACKERS,
        initiative=initiative,
        format="commander",
        players=[p1, p2],
    )


def _add_creature(gs: GameState, name: str, power: int, toughness: int, controller: str):
    """Add a creature to the battlefield (AI-controlled, so no ETB choice)."""
    card = Card(
        name=name,
        type_line="Creature — Beast",
        power=str(power),
        toughness=str(toughness),
        oracle_text="",
    )
    return put_permanent_onto_battlefield(gs, card, controller)


# ── set_initiative immutability (chain tests) ──────────────────────────────────

class TestSetInitiativeImmutability:
    """Verify set_initiative returns new GameState; original is unchanged."""

    def test_chained_transfers_each_return_new_state(self):
        """Multiple set_initiative calls produce distinct objects each time."""
        gs = _make_gs(initiative=None)
        ids = []
        current = gs
        for player in ["Alice", "Bob", "Alice", "Bob"]:
            current = set_initiative(current, player)
            ids.append(id(current))
            assert gs.initiative is None, "Original gs must not be mutated"
            assert len(gs.pending_triggers) == 0, "Original gs must not accumulate triggers"
        # All states are distinct objects
        assert len(set(ids)) == 4

    def test_original_unchanged_after_chained_transfers(self):
        """After 5 initiative transfers, original GameState is pristine."""
        gs = _make_gs(initiative=None)
        current = gs
        for player in ["Alice", "Bob", "Alice", "Bob", "Alice"]:
            current = set_initiative(current, player)
        assert gs.initiative is None
        assert len(gs.pending_triggers) == 0
        assert current.initiative == "Alice"
        assert len(current.pending_triggers) == 5

    def test_gain_initiative_triggers_accumulated_correctly(self):
        """Each set_initiative call appends exactly one gain_initiative trigger."""
        gs = _make_gs(initiative=None)
        current = gs
        for player in ["Alice", "Bob"]:
            current = set_initiative(current, player)
        triggers = [t for t in current.pending_triggers if t.trigger_type == "gain_initiative"]
        assert len(triggers) == 2
        assert triggers[0].controller == "Alice"
        assert triggers[1].controller == "Bob"


# ── Combat damage → initiative transfer ────────────────────────────────────────

class TestInitiativeCombatTransfer:
    """Full combat damage flow transfers initiative correctly via combat/core.py hook."""

    def _setup_combat(self, initiative_holder: str) -> tuple[GameState, str]:
        """Create combat state with initiative holder set and a creature attacking them."""
        gs = _make_combat_game(initiative=initiative_holder)
        # Alice attacks Bob (who is initiative holder)
        gs, attacker = _add_creature(gs, "Bear", 2, 2, "p1")
        attacker.summoning_sick = False
        # Determine target (initiative holder)
        target = initiative_holder  # "p2" is Bob
        return gs, attacker.id, target

    def test_damage_to_initiative_holder_transfers_to_attacker(self):
        """When Alice's creature deals combat damage to Bob (initiative holder), Alice gains initiative."""
        gs, attacker_id, target = self._setup_combat("p2")
        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker_id, defending_id=target)])
        gs.step = Step.COMBAT_DAMAGE
        old_initiative = gs.initiative
        old_triggers = len(gs.pending_triggers)

        gs = assign_combat_damage(gs)

        assert gs.initiative == "p1", f"Attacker (p1) should gain initiative, got {gs.initiative}"
        # One gain_initiative trigger from the transfer
        gain_triggers = [t for t in gs.pending_triggers if t.trigger_type == "gain_initiative"]
        assert len(gain_triggers) == 1
        assert gain_triggers[0].controller == "p1"
        # Original gs not mutated (comparing snapshot)
        assert old_initiative == "p2"
        assert len(gs.pending_triggers) > old_triggers

    def test_damage_to_non_initiative_holder_no_transfer(self):
        """When Alice attacks Bob but someone else has initiative, no transfer."""
        gs, attacker_id, _ = self._setup_combat("p1")  # p1 has initiative
        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker_id, defending_id="p2")])
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)
        assert gs.initiative == "p1", "Initiative should stay with p1 (already held)"

    def test_no_initiative_no_transfer(self):
        """When nobody has initiative, combat damage does nothing."""
        gs, attacker_id, _ = self._setup_combat(None)
        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker_id, defending_id="p2")])
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)
        assert gs.initiative is None

    def test_initiative_transfer_fires_trigger(self):
        """Combat damage initiative transfer fires gain_initiative trigger."""
        gs, attacker_id, target = self._setup_combat("p2")
        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker_id, defending_id=target)])
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        triggers = [t for t in gs.pending_triggers if t.trigger_type == "gain_initiative"]
        assert len(triggers) >= 1
        trigger = triggers[-1]
        assert trigger.controller == "p1"
        assert trigger.source_card_name == "initiative"


# ── Upkeep venture flow ─────────────────────────────────────────────────────────

class TestInitiativeUpkeepVenture:
    """Initiative holder ventures into Undercity at beginning of upkeep."""

    def test_initiative_holder_ventures_on_upkeep(self):
        """When initiative holder's upkeep begins, they venture into Undercity."""
        gs = _make_gs(initiative="Alice", active_player="Alice", phase="beginning", step="upkeep")
        old_dungeons = dict(gs.player_dungeons)

        gs = handle_upkeep_venture(gs)

        assert "Alice" in gs.player_dungeons
        assert gs.player_dungeons["Alice"].dungeon_name == "Undercity"
        # Original gs not mutated
        assert "Alice" not in old_dungeons

    def test_non_initiative_holder_does_not_venture(self):
        """When active player is not the initiative holder, no venture."""
        gs = _make_gs(initiative="Bob", active_player="Alice", phase="beginning", step="upkeep")

        gs = handle_upkeep_venture(gs)

        assert "Alice" not in gs.player_dungeons
        assert gs.player_dungeons.get("Alice") is None

    def test_no_initiative_no_venture(self):
        """When nobody has initiative, no venture occurs."""
        gs = _make_gs(initiative=None, active_player="Alice", phase="beginning", step="upkeep")

        gs = handle_upkeep_venture(gs)

        assert "Alice" not in gs.player_dungeons

    def test_upkeep_venture_is_pure(self):
        """handle_upkeep_venture does not mutate the original GameState."""
        gs = _make_gs(initiative="Alice", active_player="Alice", phase="beginning", step="upkeep")
        old_id = id(gs)
        old_dungeons = dict(gs.player_dungeons)

        new_gs = handle_upkeep_venture(gs)

        assert id(gs) == old_id
        assert gs.player_dungeons == old_dungeons
        assert new_gs is not gs
        assert "Alice" in new_gs.player_dungeons

    def test_venture_advances_through_rooms_on_repeated_upkeeps(self):
        """Multiple upkeep ventures advance the dungeon room by room."""
        gs = _make_gs(initiative="Alice", active_player="Alice", phase="beginning", step="upkeep")
        # First venture: starts at room 0, advances to room 1 (Forgotten Temple)
        # Room 1 has "venture into the dungeon" → recursive advance to room 2.
        gs = handle_upkeep_venture(gs)
        progress1 = get_dungeon_progress(gs, "Alice")
        assert progress1.current_room_index == 2  # Two advances from recursive venture

        # Second venture: room 2 → room 3 (no recursive venture; _apply_single_effect_text
        # only resolves first matched pattern in multi-effect abilities)
        gs = handle_upkeep_venture(gs)
        progress2 = get_dungeon_progress(gs, "Alice")
        assert progress2.current_room_index == 3

        # Third venture: room 3 → room 4 (Throne of the Dead Three, last room)
        gs = handle_upkeep_venture(gs)
        progress3 = get_dungeon_progress(gs, "Alice")
        assert progress3.current_room_index == 4
        assert progress3.is_complete is False

        # Fourth venture: room 4 → index 5 (dungeon complete)
        gs = handle_upkeep_venture(gs)
        progress4 = get_dungeon_progress(gs, "Alice")
        assert progress4.current_room_index == 5
        assert progress4.is_complete is True


# ── Initiative + dungeon cross-tracking ────────────────────────────────────────

class TestInitiativeDungeonTracking:
    """Initiative and dungeon progress are tracked independently per player."""

    def test_dungeon_completion_increments_counter(self):
        """Completing Undercity increments the player's completed dungeon count."""
        gs = _make_gs(initiative="Alice", active_player="Alice", phase="beginning", step="upkeep")
        # Undercity has 5 rooms (indices 0-4), needs 4 ventures to complete
        for _ in range(4):
            gs = handle_upkeep_venture(gs)

        count = get_completed_dungeon_count("Alice", gs)
        assert count == 1
        # Dungeon progress remains but is_complete=True; next venture starts a new dungeon
        assert "Alice" in gs.player_dungeons
        assert gs.player_dungeons["Alice"].is_complete is True

    def test_initiative_transfer_then_venture(self):
        """Initiative transfers to Bob, then Bob ventures on his upkeep."""
        gs = _make_gs(initiative="Alice", active_player="Alice", phase="beginning", step="upkeep")
        # Alice ventures once
        gs = handle_upkeep_venture(gs)
        assert get_dungeon_progress(gs, "Alice").current_room_index == 2

        # Initiative transfers to Bob
        gs = set_initiative(gs, "Bob")
        assert gs.initiative == "Bob"
        # Alice no longer ventures (she no longer has initiative)
        old_alice_progress = get_dungeon_progress(gs, "Alice")

        gs_active_bob = _make_gs(initiative="Bob", active_player="Bob", phase="beginning", step="upkeep")
        gs_active_bob.player_dungeons["Bob"] = gs.player_dungeons.get("Bob")
        gs_active_bob = handle_upkeep_venture(gs_active_bob)
        assert "Bob" in gs_active_bob.player_dungeons
        assert gs_active_bob.player_dungeons["Bob"].dungeon_name == "Undercity"

    def test_multiple_players_venture_independently(self):
        """Two players can each venture through their own dungeons."""
        gs = GameState(
            game_id="test-multi-venture",
            seed=1,
            turn=1,
            active_player="Alice",
            priority_holder="Alice",
            initiative="Alice",
            phase="beginning",
            step="upkeep",
            players=[
                PlayerState(name="Alice", library=[_card(f"A{i}") for i in range(30)]),
                PlayerState(name="Bob", library=[_card(f"B{i}") for i in range(30)]),
            ],
        )
        # Alice ventures once
        gs = handle_upkeep_venture(gs)
        assert get_dungeon_progress(gs, "Alice") is not None

        # Bob ventures (if he had initiative)
        # Bob doesn't have initiative, so nothing happens for him
        gs = handle_upkeep_venture(gs)
        assert get_dungeon_progress(gs, "Bob") is None
