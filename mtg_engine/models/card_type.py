from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CoreType(str, Enum):
    """Magic card core types (CR 205.2)."""
    ARTIFACT = "Artifact"
    BATTLE = "Battle"
    CONSPIRACY = "Conspiracy"
    CREATURE = "Creature"
    ENCHANTMENT = "Enchantment"
    INSTANT = "Instant"
    PLANE = "Plane"
    PHENOMENON = "Phenomenon"
    PLANEWALKER = "Planewalker"
    SCHEME = "Scheme"
    SOUL = "Soul"
    SPELL = "Spell"
    VANTAGE = "Vantage"
    WAR = "War"
    WORLD = "World"


class Supertype(str, Enum):
    """Magic card supertypes (CR 205.3)."""
    BASIC = "basic"
    ELDRITCH = "Eldritch"
    HOST = "Host"
    LEGENDARY = "Legendary"
    LEVELER = "Leveler"
    OMINOUS = "Ominous"
    OVERLORD = "Overlord"
    SNOW = "Snow"
    TRIBAL = "Tribal"


class EnchantmentSubtype(str, Enum):
    AURA = "Aura"
    CARTOCHE = "Cartouche"


class ArtifactSubtype(str, Enum):
    EQUIPMENT = "Equipment"
    FORTIFICATION = "Fortification"
    VEHICLE = "Vehicle"


class CardType(BaseModel):
    """Structured card type representation (CR 205)."""
    core_types: list[CoreType] = Field(default_factory=list)
    supertypes: list[Supertype] = Field(default_factory=list)
    subtypes: list[str] = Field(default_factory=list)
    subtype_groups: dict[str, list[str]] = Field(default_factory=dict)

    def is_core_type(self, ct: CoreType) -> bool:
        return ct in self.core_types

    def has_supertype(self, st: Supertype) -> bool:
        return st in self.supertypes

    def has_subtype(self, subtype: str) -> bool:
        return subtype in self.subtypes

    def has_subtypes(self, subtypes: list[str]) -> bool:
        return any(st in self.subtypes for st in subtypes)

    def add_subtype(self, subtype: str) -> None:
        if subtype not in self.subtypes:
            self.subtypes.append(subtype)

    def remove_subtype(self, subtype: str) -> None:
        if subtype in self.subtypes:
            self.subtypes.remove(subtype)

    def is_planeswalker(self) -> bool:
        return CoreType.PLANEWALKER in self.core_types

    def is_creature(self) -> bool:
        return CoreType.CREATURE in self.core_types

    def is_artifact(self) -> bool:
        return CoreType.ARTIFACT in self.core_types

    def is_enchantment(self) -> bool:
        return CoreType.ENCHANTMENT in self.core_types

    def is_instant(self) -> bool:
        return CoreType.INSTANT in self.core_types

    def is_basic_land(self) -> bool:
        return Supertype.BASIC in self.supertypes

    def is_legendary(self) -> bool:
        return Supertype.LEGENDARY in self.supertypes

    def is_snow(self) -> bool:
        return Supertype.SNOW in self.supertypes

    def is_aura(self) -> bool:
        return EnchantmentSubtype.AURA.value in self.subtypes

    def is_equipment(self) -> bool:
        return ArtifactSubtype.EQUIPMENT.value in self.subtypes

    def is_vehicle(self) -> bool:
        return ArtifactSubtype.VEHICLE.value in self.subtypes

    def is_fortification(self) -> bool:
        return ArtifactSubtype.FORTIFICATION.value in self.subtypes

    def is_saga(self) -> bool:
        return "Saga" in self.subtypes

    def is_battle(self) -> bool:
        return CoreType.BATTLE in self.core_types

    def is_cartouche(self) -> bool:
        return EnchantmentSubtype.CARTOCHE.value in self.subtypes


def parse_type_line(type_line: str) -> CardType:
    """Parse a Magic type line into a structured CardType (CR 205).

    Format: "[Supertype] [CoreType] [Subtype(s)]"
    Example: "Legendary Snow Artifact Creature — Golem Wizard"
    """
    result = CardType()
    if not type_line or not type_line.strip():
        return result

    parts = type_line.split("—")
    if len(parts) == 2:
        left = parts[0].strip()
        right = parts[1].strip()
    else:
        left = type_line.strip()
        right = ""

    # Parse left side (supertypes + core types)
    left_words = left.split()
    supertype_map = {st.value.lower(): st for st in Supertype}
    core_type_map = {ct.value.lower(): ct for ct in CoreType}

    for word in left_words:
        word_lower = word.lower()
        if word_lower in supertype_map:
            result.supertypes.append(supertype_map[word_lower])
        elif word_lower in core_type_map:
            result.core_types.append(core_type_map[word_lower])
        elif word_lower == "land":
            # Land is a core type without a specific enum entry
            pass

    # Parse right side (subtypes)
    if right:
        subtypes = right.split()
        result.subtypes = subtypes

    return result
