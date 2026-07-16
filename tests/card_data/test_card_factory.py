"""
CRD-02: CardFactory tests.
Cards can be created from oracle text without Scryfall API.
"""
from mtg_engine.card_data.card_factory import (
    create_card, make_creature, make_basic_land,
    make_instant_or_sorcery, make_enchantment, make_artifact,
)


class TestCreateCard:
    def test_minimal_card(self):
        card = create_card("Test")
        assert card.name == "Test"
        assert card.type_line == ""
        assert card.mana_cost is None
        assert card.power is None
        assert card.toughness is None
        assert card.colors == []
        assert card.cmc == 0.0
        assert card.keywords == []

    def test_mana_colors_derived(self):
        card = create_card("Lightning Bolt", mana_cost="{R}")
        assert card.colors == ["R"]

    def test_multi_color_derived(self):
        card = create_card("Rakdos", mana_cost="{B}{R}")
        assert set(card.colors) == {"B", "R"}

    def test_keywords_extracted_from_oracle(self):
        card = create_card("Test", oracle_text="Flying, vigilance. When this enters, draw.")
        assert "flying" in card.keywords
        assert "vigilance" in card.keywords

    def test_explicit_keywords_override(self):
        card = create_card("Test", keywords=["flying"], oracle_text="Trample")
        assert card.keywords == ["flying"]

    def test_explicit_colors_override(self):
        card = create_card("Test", mana_cost="{W}", colors=["U"])
        assert card.colors == ["U"]

    def test_has_unique_id(self):
        c1 = create_card("A")
        c2 = create_card("A")
        assert c1.id != c2.id

    def test_has_id_str(self):
        card = create_card("Test")
        assert isinstance(card.id, str)
        assert len(card.id) > 0


class TestMakeCreature:
    def test_basic_creature(self):
        card = make_creature("Grizzly Bears", "2", "2", mana_cost="{1}{G}")
        assert card.name == "Grizzly Bears"
        assert card.power == "2"
        assert card.toughness == "2"
        assert card.cmc == 2.0
        assert "G" in card.colors
        assert card.type_line == "Creature"

    def test_creature_with_keywords(self):
        card = make_creature("Serra Angel", "4", "4",
                              oracle_text="Flying, vigilance",
                              mana_cost="{3}{W}{W}")
        assert "flying" in card.keywords
        assert "vigilance" in card.keywords
        assert card.cmc == 5.0

    def test_creature_with_type_line(self):
        card = make_creature("Elvish Mystic", "1", "1",
                              type_line="Creature — Elf Druid",
                              mana_cost="{G}")
        assert "Elf" in card.type_line


class TestMakeBasicLand:
    def test_mountain(self):
        card = make_basic_land()
        assert card.name == "Mountain"
        assert card.colors == ["R"]
        assert card.cmc == 0.0
        assert card.keywords == []

    def test_plains(self):
        card = make_basic_land("Plains", color="W")
        assert card.colors == ["W"]

    def test_forest(self):
        card = make_basic_land("Forest", color="G")
        assert card.colors == ["G"]


class TestMakeInstantOrSorcery:
    def test_instant(self):
        card = make_instant_or_sorcery("Healing Salve",
                                        oracle_text="Target player gains 3 life.",
                                        mana_cost="{W}")
        assert card.colors == ["W"]
        assert card.type_line == "Instant"

    def test_sorcery(self):
        card = make_instant_or_sorcery("Mind Rot",
                                        oracle_text="Target player discards two cards.",
                                        mana_cost="{2}{B}",
                                        card_type="Sorcery")
        assert card.type_line == "Sorcery"
        assert "B" in card.colors


class TestMakeEnchantment:
    def test_basic_enchantment(self):
        card = make_enchantment("Glorious Anthem",
                                 oracle_text="Creatures you control get +1/+1.",
                                 mana_cost="{1}{W}{W}")
        assert card.colors == ["W"]
        assert card.type_line == "Enchantment"

    def test_aura(self):
        card = make_enchantment("Rancor",
                                 oracle_text="Enchanted creature gets +2/+0 and has trample.",
                                 mana_cost="{G}",
                                 type_line="Enchantment — Aura")
        assert "Aura" in card.type_line


class TestMakeArtifact:
    def test_basic_artifact(self):
        card = make_artifact("Sol Ring", mana_cost="{1}")
        assert card.colors == []
        assert card.cmc == 1.0

    def test_artifact_creature(self):
        card = make_artifact("Steel Golem",
                              oracle_text="You can't cast creature spells.",
                              mana_cost="{3}",
                              type_line="Artifact Creature — Golem")
        assert "Golem" in card.type_line
