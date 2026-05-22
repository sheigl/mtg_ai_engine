import pytest
from mtg_engine.models.game import Card, GameState, PlayerState, Permanent
from mtg_engine.ability.targeting import (
    parse_target_spec, validate_target_type, validate_target_count,
    get_valid_targets, TargetSpec,
)


class TestParseTargetSpec:
    def test_simple_target_creature(self):
        spec = parse_target_spec("Destroy target creature.")
        assert spec.is_targeted
        assert spec.count_min == 1
        assert spec.count_max == 1
        assert "creature" in spec.target_types

    def test_up_to_two_targets(self):
        spec = parse_target_spec("Deal 1 damage to up to 2 target creatures.")
        assert spec.is_targeted
        assert spec.count_min == 1
        assert spec.count_max == 2

    def test_single_target_player(self):
        spec = parse_target_spec("Target player loses 1 life.")
        assert spec.is_targeted
        assert "player" in spec.target_types

    def test_multiple_target_types(self):
        spec = parse_target_spec("Target player or planeswalker.")
        assert spec.is_targeted
        assert "player" in spec.target_types
        assert "planeswalker" in spec.target_types

    def test_color_restriction(self):
        spec = parse_target_spec("Destroy target black creature.")
        assert spec.is_targeted
        assert "creature" in spec.target_types
        assert "black" in spec.color_restrictions

    def test_subtype_restriction(self):
        spec = parse_target_spec("Destroy target Goblin creature.")
        assert spec.is_targeted
        assert "goblin" in [s.lower() for s in spec.subtype_restrictions]

    def test_controller_restriction(self):
        spec = parse_target_spec("Destroy target artifact an opponent controls.")
        assert spec.is_targeted
        assert "opponent_controls" in spec.controller_restrictions

    def test_no_target(self):
        spec = parse_target_spec("Creatures get +1/+1 until end of turn.")
        assert not spec.is_targeted

    def test_empty_oracle(self):
        spec = parse_target_spec("")
        assert not spec.is_targeted


class TestValidateTargetType:
    def test_valid_creature_target(self):
        gs = GameState(
            game_id="test",
            seed=42,
            players=[PlayerState(name="P1", life=20, library=[], hand=[])],
            active_player="P1",
            priority_holder="P1",
        )
        creature = Permanent(
            card=Card(name="Goblin", type_line="Creature — Goblin"),
            controller="P1",
        )
        gs.battlefield = [creature]

        spec = parse_target_spec("Destroy target creature.")
        assert validate_target_type(creature.id, gs, spec)

    def test_invalid_target_type(self):
        gs = GameState(
            game_id="test",
            seed=42,
            players=[PlayerState(name="P1", life=20, library=[], hand=[])],
            active_player="P1",
            priority_holder="P1",
        )
        artifact = Permanent(
            card=Card(name="Armor", type_line="Artifact"),
            controller="P1",
        )
        gs.battlefield = [artifact]

        spec = parse_target_spec("Destroy target creature.")
        assert not validate_target_type(artifact.id, gs, spec)

    def test_valid_player_target(self):
        gs = GameState(
            game_id="test",
            seed=42,
            players=[PlayerState(name="P1", life=20, library=[], hand=[]),
                     PlayerState(name="P2", life=20, library=[], hand=[])],
            active_player="P1",
            priority_holder="P1",
        )

        spec = parse_target_spec("Target player loses 1 life.")
        assert validate_target_type("P2", gs, spec)

    def test_color_restriction(self):
        gs = GameState(
            game_id="test",
            seed=42,
            players=[PlayerState(name="P1", life=20, library=[], hand=[])],
            active_player="P1",
            priority_holder="P1",
        )
        black_creature = Permanent(
            card=Card(name="Demon", type_line="Creature — Demon", colors=["B"]),
            controller="P1",
        )
        gs.battlefield = [black_creature]

        spec = parse_target_spec("Destroy target black creature.")
        assert validate_target_type(black_creature.id, gs, spec)


class TestValidateTargetCount:
    def test_valid_count(self):
        spec = parse_target_spec("Deal 1 damage to up to 2 target creatures.")
        assert validate_target_count(2, spec)
        assert validate_target_count(1, spec)

    def test_invalid_count_too_high(self):
        spec = parse_target_spec("Deal 1 damage to up to 2 target creatures.")
        assert not validate_target_count(3, spec)

    def test_invalid_count_too_low(self):
        spec = parse_target_spec("Deal 1 damage to up to 2 target creatures.")
        assert not validate_target_count(0, spec)

    def test_no_target_spec(self):
        spec = parse_target_spec("Creatures get +1/+1.")
        assert validate_target_count(5, spec)


class TestGetValidTargets:
    def test_get_creature_targets(self):
        gs = GameState(
            game_id="test",
            seed=42,
            players=[PlayerState(name="P1", life=20, library=[], hand=[]),
                     PlayerState(name="P2", life=20, library=[], hand=[])],
            active_player="P1",
            priority_holder="P1",
        )
        creature1 = Permanent(
            card=Card(name="Goblin", type_line="Creature — Goblin"),
            controller="P1",
        )
        creature2 = Permanent(
            card=Card(name="Elf", type_line="Creature — Elf"),
            controller="P2",
        )
        artifact = Permanent(
            card=Card(name="Armor", type_line="Artifact"),
            controller="P1",
        )
        gs.battlefield = [creature1, creature2, artifact]

        spec = parse_target_spec("Destroy target creature.")
        targets = get_valid_targets(gs, spec)
        assert len(targets) == 2
        assert creature1.id in targets
        assert creature2.id in targets
        assert artifact.id not in targets

    def test_get_player_targets(self):
        gs = GameState(
            game_id="test",
            seed=42,
            players=[PlayerState(name="P1", life=20, library=[], hand=[]),
                     PlayerState(name="P2", life=20, library=[], hand=[])],
            active_player="P1",
            priority_holder="P1",
        )

        spec = parse_target_spec("Target player loses 1 life.")
        targets = get_valid_targets(gs, spec)
        assert len(targets) == 2
        assert "P1" in targets
        assert "P2" in targets
