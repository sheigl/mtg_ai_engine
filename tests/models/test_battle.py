from mtg_engine.models.card_type import (
    CoreType, parse_type_line,
)
from mtg_engine.models.battle import (
    BattleSubtype, BattleModel, get_siege_abilities,
)


class TestBattleSubtype:
    def test_siege(self):
        assert BattleSubtype.SIEGE.value == "Siege"


class TestCardTypeBattleMethods:
    def test_is_battle_true(self):
        ct = parse_type_line("Battle — Siege")
        assert ct.is_battle()
        assert CoreType.BATTLE in ct.core_types
        assert "Siege" in ct.subtypes

    def test_is_battle_false(self):
        ct = parse_type_line("Creature — Goblin")
        assert not ct.is_battle()

    def test_is_battle_not_creature(self):
        ct = parse_type_line("Battle — Siege")
        assert ct.is_battle()
        assert not ct.is_creature()

    def test_legendary_battle(self):
        ct = parse_type_line("Legendary Battle — Siege")
        assert ct.is_legendary()
        assert ct.is_battle()
        assert "Siege" in ct.subtypes


class TestBattleModel:
    def test_create_siege_battle(self):
        battle = BattleModel(
            name="Invasion of Zendikar",
            defense_counters=4,
            protector="player1",
            controller="player2",
            subtype="Siege",
        )
        assert battle.name == "Invasion of Zendikar"
        assert battle.defense_counters == 4
        assert battle.protector == "player1"
        assert battle.controller == "player2"
        assert battle.is_siege
        assert not battle.is_defeated

    def test_damage_reduces_defense(self):
        battle = BattleModel(
            name="Invasion of Zendikar",
            defense_counters=4,
            protector="player1",
            controller="player2",
        )
        assert battle.defense_counters == 4
        battle.deal_damage(2)
        assert battle.defense_counters == 2
        assert not battle.is_defeated

    def test_damage_exactly_defeats(self):
        battle = BattleModel(
            name="Invasion of Zendikar",
            defense_counters=4,
            protector="player1",
            controller="player2",
        )
        battle.deal_damage(4)
        assert battle.defense_counters == 0
        assert battle.is_defeated

    def test_damage_exceeds_defense(self):
        battle = BattleModel(
            name="Invasion of Zendikar",
            defense_counters=4,
            protector="player1",
            controller="player2",
        )
        battle.deal_damage(6)
        assert battle.defense_counters == 0
        assert battle.is_defeated

    def test_no_defeat_at_one_defense(self):
        battle = BattleModel(
            name="Invasion of Zendikar",
            defense_counters=4,
            protector="player1",
            controller="player2",
        )
        battle.deal_damage(3)
        assert not battle.is_defeated

    def test_track_last_damage_source(self):
        battle = BattleModel(
            name="Invasion of Zendikar",
            defense_counters=4,
            protector="player1",
            controller="player2",
        )
        battle.deal_damage(2, source_controller="player3")
        assert battle.last_damage_controller == "player3"
        battle.deal_damage(2, source_controller="player4")
        assert battle.last_damage_controller == "player4"

    def test_get_siege_abilities_invasion(self):
        abilities = get_siege_abilities(
            "When the last defense counter is removed from this permanent, "
            "exile it, then you may cast it transformed without paying its mana cost."
        )
        assert abilities["exile_on_defeat"]
        assert abilities["cast_transformed"]
        assert not abilities["requires_attack"]

    def test_get_siege_abilities_custom(self):
        abilities = get_siege_abilities(
            "When the last defense counter is removed from this permanent, "
            "exile it, then you may cast it transformed."
        )
        assert abilities["exile_on_defeat"]
        assert abilities["cast_transformed"]

    def test_get_siege_abilities_no_text(self):
        abilities = get_siege_abilities("")
        assert not abilities["exile_on_defeat"]

    def test_battle_change_protector(self):
        battle = BattleModel(
            name="Invasion of Zendikar",
            defense_counters=4,
            protector="player1",
            controller="player2",
        )
        battle.change_protector("player3")
        assert battle.protector == "player3"

    def test_battle_no_protector(self):
        battle = BattleModel(
            name="Invasion of Zendikar",
            defense_counters=4,
            protector=None,
            controller="player2",
        )
        assert battle.protector is None
        assert not battle.is_defeated  # defense still > 0

    def test_battle_from_type_line(self):
        battle = BattleModel.from_type_line(
            name="Invasion of Zendikar",
            type_line="Battle — Siege",
            oracle_text="When the last defense counter is removed from this permanent, "
                        "exile it, then you may cast it transformed without paying its mana cost.",
            controller="player1",
        )
        assert battle.is_siege
        assert battle.defense_counters == 0  # default
        assert battle.subtype == "Siege"
        assert battle.controller == "player1"
        assert battle.protector is None
