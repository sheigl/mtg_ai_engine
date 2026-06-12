from mtg_engine.models.game import Card, GameState, PlayerState
from mtg_engine.ability.keywords.overload import (
    parse_overload_cost, has_overload, OverloadModel, get_overload_targets,
)


class TestParseOverloadCost:
    def test_simple_overload(self):
        cost = parse_overload_cost("Overload {3}")
        assert cost == "{3}"

    def test_colored_overload(self):
        cost = parse_overload_cost("Overload {2}{R}")
        assert cost == "{2}{R}"

    def test_generic_and_colored(self):
        cost = parse_overload_cost("Overload {1}{W}{U}")
        assert cost == "{1}{W}{U}"

    def test_no_overload(self):
        cost = parse_overload_cost("Destroy target creature.")
        assert cost is None

    def test_empty_oracle(self):
        cost = parse_overload_cost("")
        assert cost is None


class TestHasOverload:
    def test_has_overload_true(self):
        assert has_overload("Overload {3}. Destroy all creatures.")

    def test_has_overload_false(self):
        assert not has_overload("Destroy target creature.")

    def test_empty_oracle(self):
        assert not has_overload("")


class TestOverloadModel:
    def test_create_overload_model(self):
        model = OverloadModel(
            name="Blasphemous Act",
            overload_cost="{3}",
            type_line="Sorcery",
            oracle_text="Overload {3}. Destroy all creatures.",
        )
        assert model.name == "Blasphemous Act"
        assert model.overload_cost == "{3}"
        assert not model.is_overloaded

    def test_mark_overloaded(self):
        model = OverloadModel(
            name="Blasphemous Act",
            overload_cost="{3}",
            type_line="Sorcery",
            oracle_text="Overload {3}. Destroy all creatures.",
        )
        model.overload_paid = True
        assert model.is_overloaded

    def test_not_overloaded_when_no_cost(self):
        model = OverloadModel(
            name="Test",
            overload_cost=None,
            type_line="Sorcery",
            oracle_text="Destroy target creature.",
        )
        model.overload_paid = True
        assert not model.is_overloaded


class TestGetOverloadTargets:
    def test_destroy_all_creatures(self):
        # Create a minimal game state with creatures
        gs = GameState(
            game_id="test",
            seed=42,
            players=[
                PlayerState(name="Player1", life=20, library=[], hand=[]),
                PlayerState(name="Player2", life=20, library=[], hand=[]),
            ],
            active_player="Player1",
            priority_holder="Player1",
        )
        # Add some permanents
        from mtg_engine.models.game import Permanent
        creature1 = Permanent(
            card=Card(name="Goblin", type_line="Creature — Goblin"),
            controller="Player1",
        )
        creature2 = Permanent(
            card=Card(name="Elf", type_line="Creature — Elf"),
            controller="Player1",
        )
        artifact = Permanent(
            card=Card(name="Armor", type_line="Artifact"),
            controller="Player1",
        )
        gs.battlefield = [creature1, creature2, artifact]

        targets = get_overload_targets(
            "Overload {3}. Destroy all creatures.",
            gs,
        )
        assert len(targets) == 2
        assert creature1.id in targets
        assert creature2.id in targets
        assert artifact.id not in targets

    def test_target_opponent_overloaded(self):
        gs = GameState(
            game_id="test",
            seed=42,
            players=[
                PlayerState(name="Player1", life=20, library=[], hand=[]),
                PlayerState(name="Player2", life=20, library=[], hand=[]),
            ],
            active_player="Player1",
            priority_holder="Player1",
        )

        targets = get_overload_targets(
            "Overload {2}. Target opponent loses 1 life.",
            gs,
        )
        assert len(targets) == 1
        assert "Player2" in targets

    def test_no_valid_targets(self):
        gs = GameState(
            game_id="test",
            seed=42,
            players=[
                PlayerState(name="Player1", life=20, library=[], hand=[]),
            ],
            active_player="Player1",
            priority_holder="Player1",
        )

        targets = get_overload_targets(
            "Overload {3}. Destroy all creatures.",
            gs,
        )
        assert len(targets) == 0
