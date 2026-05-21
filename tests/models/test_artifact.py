import pytest
from mtg_engine.models.card_type import (
    CoreType, ArtifactSubtype, CardType, parse_type_line,
)
from mtg_engine.models.artifact import (
    parse_equip_cost, parse_crew_cost, can_equip,
    is_creature_type_line, EquipmentModel, VehicleModel,
)


class TestArtifactSubtypes:
    def test_equipment_subtype(self):
        assert ArtifactSubtype.EQUIPMENT.value == "Equipment"

    def test_vehicle_subtype(self):
        assert ArtifactSubtype.VEHICLE.value == "Vehicle"

    def test_fortification_subtype(self):
        assert ArtifactSubtype.FORTIFICATION.value == "Fortification"


class TestCardTypeArtifactMethods:
    def test_is_equipment(self):
        ct = parse_type_line("Artifact — Equipment")
        assert ct.is_artifact()
        assert ct.is_equipment()
        assert ct.is_attachment()

    def test_is_vehicle(self):
        ct = parse_type_line("Artifact — Vehicle")
        assert ct.is_artifact()
        assert ct.is_vehicle()
        assert not ct.is_attachment()

    def test_is_fortification(self):
        ct = parse_type_line("Artifact — Fortification")
        assert ct.is_artifact()
        assert ct.is_fortification()
        assert ct.is_attachment()

    def test_artifact_creature(self):
        ct = parse_type_line("Artifact Creature — Golem")
        assert ct.is_artifact()
        assert ct.is_creature()

    def test_legendary_artifact_equipment(self):
        ct = parse_type_line("Legendary Artifact — Equipment")
        assert ct.is_legendary()
        assert ct.is_artifact()
        assert ct.is_equipment()

    def test_equipment_not_aura(self):
        ct = parse_type_line("Artifact — Equipment")
        assert ct.is_equipment()
        assert not ct.is_aura()


class TestParseEquipCost:
    def test_equip_one(self):
        cost = parse_equip_cost("Equip {1}")
        assert cost == "{1}"

    def test_equip_zero(self):
        cost = parse_equip_cost("Equip {0}")
        assert cost == "{0}"

    def test_equip_colored_mana(self):
        cost = parse_equip_cost("Equip {W}")
        assert cost == "{W}"

    def test_equip_generic_and_colored(self):
        cost = parse_equip_cost("Equip {2}{R}")
        assert cost == "{2}{R}"

    def test_equip_sacrifice(self):
        cost = parse_equip_cost("Equip—Sacrifice a creature.")
        assert cost == "Sacrifice a creature"

    def test_no_equip_cost(self):
        cost = parse_equip_cost("Equipped creature gets +1/+1.")
        assert cost is None

    def test_empty_oracle(self):
        cost = parse_equip_cost("")
        assert cost is None

    def test_living_weapon_no_equip(self):
        cost = parse_equip_cost(
            "Living weapon (When this Equipment enters the battlefield, "
            "create a 0/0 black Phyrexian Germ creature token, then "
            "attach this to it.)"
        )
        assert cost is None

    def test_equip_with_restriction(self):
        cost = parse_equip_cost("Equip {2}. Equip only as a sorcery.")
        assert cost == "{2}"


class TestParseCrewCost:
    def test_crew_3(self):
        crew = parse_crew_cost("Crew 3")
        assert crew == 3

    def test_crew_1(self):
        crew = parse_crew_cost("Crew 1")
        assert crew == 1

    def test_crew_5(self):
        crew = parse_crew_cost("Crew 5")
        assert crew == 5

    def test_no_crew(self):
        crew = parse_crew_cost("Flying, trample")
        assert crew == 0

    def test_empty_oracle(self):
        crew = parse_crew_cost("")
        assert crew == 0

    def test_artifact_creature_no_crew(self):
        crew = parse_crew_cost(
            "Haste\nWhen this creature enters, ..."
        )
        assert crew == 0


class TestCanEquip:
    def test_equip_creature(self):
        assert can_equip("Artifact — Equipment", "Creature — Goblin")

    def test_equip_legendary_creature(self):
        assert can_equip("Artifact — Equipment", "Legendary Creature — Dragon")

    def test_cannot_equip_artifact(self):
        assert not can_equip("Artifact — Equipment", "Artifact")

    def test_cannot_equip_land(self):
        assert not can_equip("Artifact — Equipment", "Land")

    def test_cannot_equip_enchantment(self):
        assert not can_equip("Artifact — Equipment", "Enchantment")

    def test_cannot_equip_planeswalker(self):
        assert not can_equip("Artifact — Equipment", "Planewalker")

    def test_non_equipment_cannot_equip(self):
        assert not can_equip("Artifact — Vehicle", "Creature — Goblin")

    def test_cannot_equip_battle(self):
        assert not can_equip("Artifact — Equipment", "Battle — Siege")


class TestIsCreatureTypeLine:
    def test_creature(self):
        assert is_creature_type_line("Creature — Goblin")

    def test_artifact_creature(self):
        assert is_creature_type_line("Artifact Creature — Golem")

    def test_artifact(self):
        assert not is_creature_type_line("Artifact — Equipment")

    def test_enchantment(self):
        assert not is_creature_type_line("Enchantment — Aura")

    def test_land(self):
        assert not is_creature_type_line("Land")

    def test_crewed_vehicle(self):
        # Vehicle is not a creature until crewed
        assert not is_creature_type_line("Artifact — Vehicle")

    def test_legendary_creature(self):
        assert is_creature_type_line("Legendary Creature — Dragon")


class TestEquipmentModel:
    def test_create_equipment_model(self):
        equip = EquipmentModel(
            name="Colossus Hammer",
            equip_cost="{1}",
            type_line="Artifact — Equipment",
        )
        assert equip.name == "Colossus Hammer"
        assert equip.equip_cost == "{1}"
        assert equip.type_line == "Artifact — Equipment"
        assert equip.can_attach

    def test_equipment_with_abilities(self):
        equip = EquipmentModel(
            name="Loxodon Warhammer",
            equip_cost="{3}",
            type_line="Artifact — Equipment",
            granted_keywords=["trample", "lifelink"],
            power_bonus=3,
            toughness_bonus=0,
        )
        assert "trample" in equip.granted_keywords
        assert equip.power_bonus == 3

    def test_equipment_no_bonus(self):
        equip = EquipmentModel(
            name="Swiftfoot Boots",
            equip_cost="{1}",
            type_line="Artifact — Equipment",
        )
        assert equip.power_bonus == 0
        assert equip.toughness_bonus == 0


class TestVehicleModel:
    def test_create_vehicle_model(self):
        vehicle = VehicleModel(
            name="Smuggler's Copter",
            crew_cost=3,
            type_line="Artifact — Vehicle",
            power=3,
            toughness=3,
        )
        assert vehicle.name == "Smuggler's Copter"
        assert vehicle.crew_cost == 3
        assert not vehicle.is_creature

    def test_crew_vehicle(self):
        vehicle = VehicleModel(
            name="Smuggler's Copter",
            crew_cost=3,
            type_line="Artifact — Vehicle",
            power=3,
            toughness=3,
        )
        assert not vehicle.is_creature
        vehicle.crew()
        assert vehicle.is_creature
        assert vehicle.crewed_this_turn

    def test_uncrew_vehicle(self):
        vehicle = VehicleModel(
            name="Smuggler's Copter",
            crew_cost=3,
            type_line="Artifact — Vehicle",
            power=3,
            toughness=3,
        )
        vehicle.crew()
        assert vehicle.is_creature
        vehicle.uncrew()
        assert not vehicle.is_creature
        assert not vehicle.crewed_this_turn

    def test_vehicle_cannot_crew_twice(self):
        vehicle = VehicleModel(
            name="Smuggler's Copter",
            crew_cost=3,
            type_line="Artifact — Vehicle",
            power=3,
            toughness=3,
        )
        assert vehicle.can_crew(3)
        vehicle.crew()
        assert vehicle.crewed_this_turn
        assert not vehicle.can_crew(3)

    def test_vehicle_needs_sufficient_power(self):
        vehicle = VehicleModel(
            name="Aeronaut Admiral",
            crew_cost=3,
            type_line="Artifact — Vehicle",
            power=3,
            toughness=3,
        )
        assert not vehicle.can_crew(2)
        assert vehicle.can_crew(3)
        assert vehicle.can_crew(5)

    def test_vehicle_crew_with_exact_power(self):
        vehicle = VehicleModel(
            name="Consulate Dreadnought",
            crew_cost=6,
            type_line="Artifact — Vehicle",
            power=7,
            toughness=11,
        )
        assert vehicle.can_crew(6)
        assert not vehicle.can_crew(5)
