"""
Dungeon data model for the Venture mechanic (VEN-01).
AFR (Adventures in the Forgotten Realms) dungeons.

Each dungeon is a list of rooms. Venturing advances to the next room.
Completing the final room triggers the dungeon completion reward.
"""
from typing import Optional
from pydantic import BaseModel, Field


class Room(BaseModel):
    """A single room in a dungeon."""
    name: str
    index: int
    ability: str


class Dungeon(BaseModel):
    """A complete dungeon with its rooms."""
    name: str
    rooms: list[Room]

    def total_rooms(self) -> int:
        return len(self.rooms)

    def get_room(self, index: int) -> Optional[Room]:
        if 0 <= index < len(self.rooms):
            return self.rooms[index]
        return None


DUNGEON_OF_THE_MAD_MAGE = Dungeon(
    name="Dungeon of the Mad Mage",
    rooms=[
        Room(index=0, name="Yawning Portal",
             ability="Scry 1"),
        Room(index=1, name="Dungeon Level",
             ability="Draw a card, then lose 1 life"),
        Room(index=2, name="Mad Mage",
             ability="Return target creature card from your graveyard to the battlefield"),
    ],
)

LOST_MINE_OF_PHANDELEVER = Dungeon(
    name="Lost Mine of Phandelver",
    rooms=[
        Room(index=0, name="Cave Entrance",
             ability="Create a 1/1 green Goblin creature token"),
        Room(index=1, name="Goblin Lair",
             ability="Target opponent loses 1 life. You gain 1 life"),
        Room(index=2, name="Storeroom",
             ability="Scry 2, then draw a card"),
        Room(index=3, name="Temple of Dumathoin",
             ability="Target creature gets +1/+0 and gains first strike until end of turn"),
    ],
)

TOMB_OF_ANNIHILATION = Dungeon(
    name="Tomb of Annihilation",
    rooms=[
        Room(index=0, name="Catacombs",
             ability="Each opponent loses 1 life. You gain 1 life"),
        Room(index=1, name="Oubliette",
             ability="Exile target creature card from a graveyard. You gain 1 life"),
        Room(index=2, name="Sanctum",
             ability="Draw a card"),
        Room(index=3, name="Atropal",
             ability="Target creature gains deathtouch and lifelink until end of turn"),
    ],
)

ALL_DUNGEONS: list[Dungeon] = [
    DUNGEON_OF_THE_MAD_MAGE,
    LOST_MINE_OF_PHANDELEVER,
    TOMB_OF_ANNIHILATION,
]

DUNGEON_MAP: dict[str, Dungeon] = {
    d.name: d for d in ALL_DUNGEONS
}


class DungeonProgress(BaseModel):
    """Tracks a player's progress through a dungeon."""
    dungeon_name: str
    current_room_index: int = 0

    @property
    def is_complete(self) -> bool:
        dungeon = DUNGEON_MAP.get(self.dungeon_name)
        if dungeon is None:
            return True
        return self.current_room_index >= dungeon.total_rooms()

    @property
    def current_room(self) -> Optional[Room]:
        dungeon = DUNGEON_MAP.get(self.dungeon_name)
        if dungeon is None:
            return None
        return dungeon.get_room(self.current_room_index)

    def advance(self) -> "DungeonProgress":
        return DungeonProgress(
            dungeon_name=self.dungeon_name,
            current_room_index=self.current_room_index + 1,
        )
