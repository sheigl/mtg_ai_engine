import pytest
from mtg_engine.models.card_type import (
    CoreType, Supertype, EnchantmentSubtype, CardType, parse_type_line,
)
from mtg_engine.models.enchantment import (
    AuraTargetType, AuraTarget, parse_aura_target, is_aura_type_line,
)


class TestEnchantmentSubtypes:
    def test_aura_subtype(self):
        assert EnchantmentSubtype.AURA.value == "Aura"

    def test_saga_subtype(self):
        assert EnchantmentSubtype.SAGA.value == "Saga"

    def test_shrine_subtype(self):
        assert EnchantmentSubtype.SHRINE.value == "Shrine"

    def test_class_subtype(self):
        assert EnchantmentSubtype.CLASS.value == "Class"

    def test_case_subtype(self):
        assert EnchantmentSubtype.CASE.value == "Case"

    def test_curse_subtype(self):
        assert EnchantmentSubtype.CURSE.value == "Curse"

    def test_background_subtype(self):
        assert EnchantmentSubtype.BACKGROUND.value == "Background"

    def test_rune_subtype(self):
        assert EnchantmentSubtype.RUNE.value == "Rune"

    def test_role_subtype(self):
        assert EnchantmentSubtype.ROLE.value == "Role"

    def test_estate_subtype(self):
        assert EnchantmentSubtype.ESTATE.value == "Estate"

    def test_shire_subtype(self):
        assert EnchantmentSubtype.SHIRE.value == "Shire"


class TestCardTypeEnchantmentMethods:
    def test_is_aura_true(self):
        ct = parse_type_line("Enchantment — Aura")
        assert ct.is_enchantment()
        assert ct.is_aura()

    def test_is_aura_false_for_creature(self):
        ct = parse_type_line("Creature — Goblin")
        assert not ct.is_aura()

    def test_is_aura_false_for_saga(self):
        ct = parse_type_line("Enchantment — Saga")
        assert not ct.is_aura()

    def test_is_saga_true(self):
        ct = parse_type_line("Enchantment — Saga")
        assert ct.is_saga()
        assert ct.is_enchantment()

    def test_is_cartouche_true(self):
        ct = parse_type_line("Enchantment — Cartouche")
        assert ct.is_cartouche()
        assert ct.is_enchantment()

    def test_is_attachment_aura(self):
        ct = parse_type_line("Enchantment — Aura")
        assert ct.is_attachment()

    def test_is_attachment_not_for_saga(self):
        ct = parse_type_line("Enchantment — Saga")
        assert not ct.is_attachment()

    def test_is_attachment_equipment(self):
        ct = parse_type_line("Artifact — Equipment")
        assert ct.is_attachment()

    def test_legendary_enchantment_aura(self):
        ct = parse_type_line("Legendary Enchantment — Aura")
        assert ct.is_legendary()
        assert ct.is_enchantment()
        assert ct.is_aura()
        assert ct.is_attachment()

    def test_parse_snow_enchantment(self):
        ct = parse_type_line("Snow Enchantment")
        assert ct.is_snow()
        assert ct.is_enchantment()


class TestParseAuraTarget:
    def test_enchant_creature(self):
        target = parse_aura_target("Enchant creature")
        assert AuraTargetType.CREATURE in target.target_types
        assert target.can_enchant_permanent("Creature")
        assert not target.can_enchant_permanent("Land")
        assert not target.can_enchant_player()

    def test_enchant_land(self):
        target = parse_aura_target("Enchant land")
        assert AuraTargetType.LAND in target.target_types
        assert target.can_enchant_permanent("Land")
        assert not target.can_enchant_permanent("Creature")

    def test_enchant_artifact(self):
        target = parse_aura_target("Enchant artifact")
        assert AuraTargetType.ARTIFACT in target.target_types
        assert target.can_enchant_permanent("Artifact")
        assert not target.can_enchant_permanent("Creature")

    def test_enchant_enchantment(self):
        target = parse_aura_target("Enchant enchantment")
        assert AuraTargetType.ENCHANTMENT in target.target_types
        assert target.can_enchant_permanent("Enchantment")
        assert not target.can_enchant_permanent("Creature")

    def test_enchant_planeswalker(self):
        target = parse_aura_target("Enchant planeswalker")
        assert AuraTargetType.PLANESWALKER in target.target_types
        assert target.can_enchant_permanent("Planewalker")

    def test_enchant_permanent(self):
        target = parse_aura_target("Enchant permanent")
        assert target.can_enchant_anything
        assert target.can_enchant_permanent("Creature")
        assert target.can_enchant_permanent("Artifact")
        assert target.can_enchant_permanent("Enchantment")

    def test_enchant_player(self):
        target = parse_aura_target("Enchant player")
        assert target.can_enchant_player()
        assert not target.can_enchant_permanent("Creature")

    def test_enchant_creature_you_control(self):
        target = parse_aura_target("Enchant creature you control")
        assert AuraTargetType.CREATURE in target.target_types
        assert target.control_restriction == "you_control"
        assert target.can_enchant_permanent("Creature")

    def test_enchant_creature_opponent_controls(self):
        target = parse_aura_target("Enchant creature an opponent controls")
        assert AuraTargetType.CREATURE in target.target_types
        assert target.control_restriction == "opponent_controls"

    def test_enchant_creature_type_restriction(self):
        target = parse_aura_target("Enchant Goblin")
        assert AuraTargetType.CREATURE in target.target_types
        assert target.creature_type_restriction == "Goblin"
        assert target.requires_creature_type("Goblin")
        assert not target.requires_creature_type("Elf")
        assert target.can_enchant_permanent("Creature — Goblin")

    def test_enchant_target_creature(self):
        target = parse_aura_target("Enchant target creature")
        assert AuraTargetType.CREATURE in target.target_types

    def test_no_oracle_text(self):
        target = parse_aura_target("")
        assert not target.target_types
        assert not target.can_enchant_permanent("Creature")

    def test_no_enchant_keyword(self):
        target = parse_aura_target("Creatures get +1/+1")
        assert not target.target_types
        assert not target.can_enchant_permanent("Creature")

    def test_control_magic(self):
        target = parse_aura_target(
            "Enchant creature\nYou control enchanted creature."
        )
        assert AuraTargetType.CREATURE in target.target_types
        assert target.can_enchant_permanent("Creature")
        assert not target.can_enchant_permanent("Land")

    def test_rancor(self):
        target = parse_aura_target(
            "Enchant creature\n"
            "Enchanted creature gets +2/+0 and has trample.\n"
            "When Rancor is put into a graveyard from the battlefield, "
            "return Rancor to its owner's hand."
        )
        assert AuraTargetType.CREATURE in target.target_types
        assert target.can_enchant_permanent("Creature")

    def test_imprisoned_in_the_moon(self):
        target = parse_aura_target(
            "Enchant creature, land, or planeswalker\n"
            "Enchanted permanent is a colorless land with "
            "\"{T}: Add {C}\" and loses all other card types and abilities."
        )
        assert AuraTargetType.CREATURE in target.target_types
        assert AuraTargetType.LAND in target.target_types
        assert AuraTargetType.PLANESWALKER in target.target_types
        assert target.can_enchant_permanent("Creature")
        assert target.can_enchant_permanent("Land")

    def test_enchant_battle(self):
        target = parse_aura_target("Enchant battle")
        assert AuraTargetType.BATTLE in target.target_types
        assert target.can_enchant_permanent("Battle")


class TestIsAuraTypeLine:
    def test_aura_type_line(self):
        assert is_aura_type_line("Enchantment — Aura")

    def test_aura_with_supertypes(self):
        assert is_aura_type_line("Legendary Enchantment — Aura")

    def test_non_aura_enchantment(self):
        assert not is_aura_type_line("Enchantment — Saga")

    def test_non_enchantment(self):
        assert not is_aura_type_line("Creature — Goblin")

    def test_empty_string(self):
        assert not is_aura_type_line("")


class TestAuraTargetMethods:
    def test_can_enchant_specific_type(self):
        target = AuraTarget(target_types=[AuraTargetType.CREATURE])
        assert target.can_enchant(AuraTargetType.CREATURE)
        assert not target.can_enchant(AuraTargetType.LAND)

    def test_can_enchant_multiple(self):
        target = AuraTarget(
            target_types=[AuraTargetType.CREATURE, AuraTargetType.LAND]
        )
        assert target.can_enchant(AuraTargetType.CREATURE)
        assert target.can_enchant(AuraTargetType.LAND)
        assert not target.can_enchant(AuraTargetType.ARTIFACT)

    def test_requires_creature_type_none(self):
        target = AuraTarget(target_types=[AuraTargetType.CREATURE])
        assert not target.requires_creature_type("Goblin")

    def test_requires_creature_type_case_insensitive(self):
        target = AuraTarget(
            target_types=[AuraTargetType.CREATURE],
            creature_type_restriction="Goblin",
        )
        assert target.requires_creature_type("goblin")
        assert target.requires_creature_type("Goblin")
        assert not target.requires_creature_type("Dragon")
