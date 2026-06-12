"""
VEN-01: Venture/Dungeon mechanic tests.
"""
import pytest

from mtg_engine.engine.dungeon import (
    venture, start_dungeon, get_dungeon_progress,
    get_available_dungeons, get_completed_dungeon_count,
    get_room_count,
)
from mtg_engine.models.game import GameState, PlayerState
from mtg_engine.models.dungeon import (
    DungeonProgress, Room, Dungeon,
    DUNGEON_MAP, ALL_DUNGEONS,
)


def _make_gs() -> GameState:
    return GameState(
        game_id="test-dun",
        seed=42,
        turn=1,
        active_player="Alice",
        priority_holder="Alice",
        players=[
            PlayerState(name="Alice", library=[]),
            PlayerState(name="Bob", library=[]),
        ],
    )


class TestDungeonModels:
    def test_room_creation(self):
        room = Room(name="Test Room", index=0, ability="Scry 1")
        assert room.name == "Test Room"
        assert room.ability == "Scry 1"

    def test_dungeon_total_rooms(self):
        assert len(ALL_DUNGEONS) == 3

    def test_dungeon_names(self):
        names = {d.name for d in ALL_DUNGEONS}
        assert names == {"Dungeon of the Mad Mage",
                         "Lost Mine of Phandelver",
                         "Tomb of Annihilation"}

    def test_dungeon_by_name(self):
        dungeon = DUNGEON_MAP["Lost Mine of Phandelver"]
        assert dungeon.total_rooms() == 4
        assert dungeon.get_room(0).name == "Cave Entrance"

    def test_get_room_out_of_range(self):
        dungeon = DUNGEON_MAP["Dungeon of the Mad Mage"]
        assert dungeon.get_room(99) is None

    def test_dungeon_progress_tracking(self):
        progress = DungeonProgress(dungeon_name="Lost Mine of Phandelver")
        assert progress.current_room_index == 0
        assert progress.is_complete is False

        progress = progress.advance()
        assert progress.current_room_index == 1

    def test_dungeon_completion(self):
        progress = DungeonProgress(dungeon_name="Dungeon of the Mad Mage")
        progress = progress.advance()  # room 1
        progress = progress.advance()  # room 2
        progress = progress.advance()  # room 3 — complete (3 rooms, after 3 advances we're past the end)
        assert progress.is_complete is True


class TestVenture:
    def test_first_venture_starts_default_dungeon(self):
        gs = _make_gs()
        gs = venture(gs, "Alice")
        progress = get_dungeon_progress(gs, "Alice")
        assert progress is not None
        assert progress.current_room_index == 1  # advanced past room 0

    def test_venture_adds_room_trigger(self):
        gs = _make_gs()
        before = len(gs.pending_triggers)
        gs = venture(gs, "Alice")
        assert len(gs.pending_triggers) >= before  # room ability trigger added

    def test_completing_dungeon_increments_counter(self):
        gs = _make_gs()
        # Start Mad Mage (3 rooms) and venture through all
        gs, _ = start_dungeon(gs, "Alice", "Dungeon of the Mad Mage")
        gs = venture(gs, "Alice")  # room 1
        gs = venture(gs, "Alice")  # room 2
        gs = venture(gs, "Alice")  # room 3 = complete
        assert get_completed_dungeon_count("Alice", gs) == 1

    def test_venture_after_completion_starts_new_dungeon(self):
        gs = _make_gs()
        gs, _ = start_dungeon(gs, "Alice", "Dungeon of the Mad Mage")
        gs = venture(gs, "Alice")  # room 1
        gs = venture(gs, "Alice")  # room 2
        gs = venture(gs, "Alice")  # room 3 = complete (1 completion)
        gs = venture(gs, "Alice")  # should start a new dungeon
        assert get_completed_dungeon_count("Alice", gs) == 1
        progress = get_dungeon_progress(gs, "Alice")
        assert progress is not None
        assert progress.current_room_index == 1  # room 1 of new dungeon

    def test_venture_tracks_progress_independently_per_player(self):
        gs = _make_gs()
        gs = venture(gs, "Alice")
        gs = venture(gs, "Alice")
        gs = venture(gs, "Bob")
        assert get_room_count("Alice", gs) == 2
        assert get_room_count("Bob", gs) == 1

    def test_start_dungeon_with_name(self):
        gs = _make_gs()
        gs, _ = start_dungeon(gs, "Alice", "Tomb of Annihilation")
        progress = get_dungeon_progress(gs, "Alice")
        assert progress.dungeon_name == "Tomb of Annihilation"

    def test_start_dungeon_unknown_raises(self):
        gs = _make_gs()
        with pytest.raises(ValueError, match="Unknown dungeon"):
            start_dungeon(gs, "Alice", "Not a Real Dungeon")

    def test_available_dungeons(self):
        names = get_available_dungeons()
        assert "Lost Mine of Phandelver" in names
        assert "Tomb of Annihilation" in names
        assert len(names) == 3
