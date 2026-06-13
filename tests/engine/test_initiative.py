"""
INT-01: The Initiative mechanic tests.
CR 702.148
"""
import pytest

from mtg_engine.engine.initiative import set_initiative, handle_upkeep_venture, check_combat_damage_initiative
from mtg_engine.models.game import GameState, PlayerState, Card


def _make_gs(initiative: str | None = None, active_player: str = "Alice") -> GameState:
    return GameState(
        game_id="test-initiative",
        seed=42,
        turn=1,
        active_player=active_player,
        priority_holder=active_player,
        initiative=initiative,
        players=[
            PlayerState(name="Alice", library=[_card(f"A{i}") for i in range(30)]),
            PlayerState(name="Bob", library=[_card(f"B{i}") for i in range(30)]),
        ],
    )


def _card(name: str) -> Card:
    return Card(id=f"id-{name}", name=name, cmc=0.0)


class TestSetInitiative:
    def test_sets_initiative(self):
        gs = _make_gs()
        gs = set_initiative(gs, "Alice")
        assert gs.initiative == "Alice"

    def test_noop_if_already_initiative(self):
        gs = _make_gs(initiative="Alice")
        before = len(gs.pending_triggers)
        gs = set_initiative(gs, "Alice")
        assert gs.initiative == "Alice"
        assert len(gs.pending_triggers) == before

    def test_changes_initiative(self):
        gs = _make_gs(initiative="Alice")
        gs = set_initiative(gs, "Bob")
        assert gs.initiative == "Bob"

    def test_fires_gain_initiative_trigger(self):
        gs = _make_gs()
        gs = set_initiative(gs, "Alice")
        triggers = [t for t in gs.pending_triggers if t.trigger_type == "gain_initiative"]
        assert len(triggers) >= 1
        assert triggers[-1].controller == "Alice"


class TestUpkeepVenture:
    def test_no_initiative_no_venture(self):
        gs = _make_gs(initiative=None)
        gs = handle_upkeep_venture(gs)
        assert "Alice" not in gs.player_dungeons

    def test_active_player_not_holder_no_venture(self):
        gs = _make_gs(initiative="Bob", active_player="Alice")
        gs = handle_upkeep_venture(gs)
        assert "Alice" not in gs.player_dungeons

    def test_initiative_holder_ventures_on_own_upkeep(self):
        gs = _make_gs(initiative="Alice", active_player="Alice")
        gs = handle_upkeep_venture(gs)
        assert "Alice" in gs.player_dungeons
        progress = gs.player_dungeons["Alice"]
        assert progress.dungeon_name == "Undercity"
        # First venture starts dungeon at room 0, then advances to room 1
        assert progress.current_room_index == 1

    def test_repeated_ventures_advance_rooms(self):
        gs = _make_gs(initiative="Alice", active_player="Alice")
        gs = handle_upkeep_venture(gs)
        assert gs.player_dungeons["Alice"].current_room_index == 1
        gs = handle_upkeep_venture(gs)
        assert gs.player_dungeons["Alice"].current_room_index == 2

    def test_completed_dungeon_stops_advancing(self):
        from mtg_engine.models.dungeon import DUNGEON_MAP, DungeonProgress
        gs = _make_gs(initiative="Alice", active_player="Alice")
        dungeon = DUNGEON_MAP["Undercity"]
        gs.player_dungeons["Alice"] = DungeonProgress(
            dungeon_name="Undercity",
            current_room_index=dungeon.total_rooms() - 1,
        )
        gs = handle_upkeep_venture(gs)
        assert "Alice" in gs.player_completed_dungeons


class TestCombatDamageInitiative:
    def test_damage_to_holder_transfers(self):
        gs = _make_gs(initiative="Bob")
        gs = check_combat_damage_initiative(gs, "Bob", "Alice")
        assert gs.initiative == "Alice"

    def test_damage_to_non_holder_no_change(self):
        gs = _make_gs(initiative="Bob")
        gs = check_combat_damage_initiative(gs, "Alice", "Charlie")
        assert gs.initiative == "Bob"

    def test_no_initiative_no_change(self):
        gs = _make_gs(initiative=None)
        gs = check_combat_damage_initiative(gs, "Alice", "Bob")
        assert gs.initiative is None

    def test_attacker_already_holder_noop(self):
        gs = _make_gs(initiative="Alice")
        gs = check_combat_damage_initiative(gs, "Alice", "Alice")
        assert gs.initiative == "Alice"
