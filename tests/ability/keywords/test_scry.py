from mtg_engine.ability.keywords.scry import Scry


class TestScryKeyword:
    def test_has_scry_true(self):
        assert Scry.has_scry(["scry"])

    def test_has_scry_false(self):
        assert not Scry.has_scry(["flying", "haste"])

    def test_has_scry_case_insensitive(self):
        assert Scry.has_scry(["Scry"])

    def test_from_oracle_text_true(self):
        assert Scry.from_oracle_text("Scry 2, then draw a card.")

    def test_from_oracle_text_false(self):
        assert not Scry.from_oracle_text("Flying.")

    def test_from_oracle_text_empty(self):
        assert not Scry.from_oracle_text("")

    def test_parse_scry_value(self):
        assert Scry.parse_scry_value("Scry 3, then draw.") == 3

    def test_parse_scry_value_default(self):
        assert Scry.parse_scry_value("Scry, then draw.") == 1

    def test_parse_scry_value_no_scry(self):
        assert Scry.parse_scry_value("Flying.") == 1

    def test_parse_scry_value_empty(self):
        assert Scry.parse_scry_value("") == 1

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Sorcery", keywords=["scry"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Scry()
        assert kw.applies(gs, perm) is True
