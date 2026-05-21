import pytest
from mtg_engine.models.card_type import (
    CoreType, Supertype, EnchantmentSubtype, ArtifactSubtype,
    CardType, parse_type_line
)


class TestParseTypeLine:
    def test_planeswalker_basic(self):
        ct = parse_type_line("Planewalker — Human")
        assert ct.is_planeswalker()
        assert CoreType.PLANEWALKER in ct.core_types
        assert "Human" in ct.subtypes

    def test_legendary_creature(self):
        ct = parse_type_line("Legendary Creature — Dragon")
        assert ct.is_creature()
        assert ct.is_legendary()
        assert "Dragon" in ct.subtypes
        assert CoreType.CREATURE in ct.core_types
        assert Supertype.LEGENDARY in ct.supertypes

    def test_artifact_creature_with_multiple_subtypes(self):
        ct = parse_type_line("Legendary Snow Artifact Creature — Golem Wizard")
        assert ct.is_artifact()
        assert ct.is_creature()
        assert ct.is_legendary()
        assert ct.is_snow()
        assert "Golem" in ct.subtypes
        assert "Wizard" in ct.subtypes

    def test_enchantment_aura(self):
        ct = parse_type_line("Enchantment — Aura")
        assert ct.is_enchantment()
        assert ct.is_aura()
        assert "Aura" in ct.subtypes

    def test_artifact_equipment(self):
        ct = parse_type_line("Artifact — Equipment")
        assert ct.is_artifact()
        assert ct.is_equipment()
        assert CoreType.ARTIFACT in ct.core_types
        assert ArtifactSubtype.EQUIPMENT.value in ct.subtypes

    def test_artifact_vehicle(self):
        ct = parse_type_line("Artifact — Vehicle")
        assert ct.is_artifact()
        assert ct.is_vehicle()

    def test_enchantment_saga(self):
        ct = parse_type_line("Enchantment — Saga")
        assert ct.is_enchantment()
        assert ct.is_saga()

    def test_basic_land(self):
        ct = parse_type_line("Basic Land — Island")
        assert ct.is_basic_land()
        assert "Island" in ct.subtypes

    def test_instant(self):
        ct = parse_type_line("Instant")
        assert ct.is_instant()
        assert not ct.is_creature()
        assert not ct.is_planeswalker()

    def test_empty_type_line(self):
        ct = parse_type_line("")
        assert not ct.core_types
        assert not ct.supertypes
        assert not ct.subtypes

    def test_none_type_line(self):
        ct = parse_type_line(None)  # type: ignore
        assert not ct.core_types

    def test_type_line_no_subtypes(self):
        ct = parse_type_line("Instant")
        assert ct.is_instant()
        assert len(ct.subtypes) == 0

    def test_battle(self):
        ct = parse_type_line("Battle — Siege")
        assert ct.is_battle()
        assert CoreType.BATTLE in ct.core_types
        assert "Siege" in ct.subtypes

    def test_snow_enchantment(self):
        ct = parse_type_line("Snow Enchantment")
        assert ct.is_enchantment()
        assert ct.is_snow()
        assert Supertype.SNOW in ct.supertypes


class TestCardTypeMethods:
    def test_add_subtype(self):
        ct = CardType()
        ct.add_subtype("Goblin")
        assert ct.has_subtype("Goblin")
        ct.add_subtype("Goblin")
        assert ct.subtypes.count("Goblin") == 1

    def test_remove_subtype(self):
        ct = CardType(subtypes=["Goblin", "Warrior"])
        ct.remove_subtype("Goblin")
        assert not ct.has_subtype("Goblin")
        assert ct.has_subtype("Warrior")

    def test_has_subtypes_any_match(self):
        ct = CardType(subtypes=["Goblin", "Warrior"])
        assert ct.has_subtypes(["Elf", "Goblin"])
        assert not ct.has_subtypes(["Elf", "Dwarf"])

    def test_is_equipment_false_for_non_equipment(self):
        ct = CardType(core_types=[CoreType.ARTIFACT], subtypes=["Vehicle"])
        assert ct.is_artifact()
        assert not ct.is_equipment()
        assert ct.is_vehicle()

    def test_is_planeswalker_false_for_creature(self):
        ct = CardType(core_types=[CoreType.CREATURE])
        assert ct.is_creature()
        assert not ct.is_planeswalker()


class TestCoreTypeEnum:
    def test_core_type_values(self):
        assert CoreType.ARTIFACT.value == "Artifact"
        assert CoreType.CREATURE.value == "Creature"
        assert CoreType.PLANEWALKER.value == "Planewalker"
        assert CoreType.ENCHANTMENT.value == "Enchantment"
        assert CoreType.INSTANT.value == "Instant"
        assert CoreType.BATTLE.value == "Battle"

    def test_core_type_in_list(self):
        types = [CoreType.ARTIFACT, CoreType.CREATURE]
        assert CoreType.ARTIFACT in types
        assert CoreType.CREATURE in types
        assert CoreType.ENCHANTMENT not in types


class TestSupertypeEnum:
    def test_supertype_values(self):
        assert Supertype.LEGENDARY.value == "Legendary"
        assert Supertype.SNOW.value == "Snow"
        assert Supertype.BASIC.value == "basic"

    def test_supertype_in_list(self):
        types = [Supertype.LEGENDARY, Supertype.SNOW]
        assert Supertype.LEGENDARY in types
        assert Supertype.SNOW in types
        assert Supertype.BASIC not in types
