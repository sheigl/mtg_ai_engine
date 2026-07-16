from mtg_engine.ability.keywords.kicker import Kicker


class TestKickerKeyword:
    def test_has_kicker_true(self):
        assert Kicker.has_kicker(["kicker"])

    def test_has_kicker_false(self):
        assert not Kicker.has_kicker(["flying", "haste"])

    def test_has_kicker_case_insensitive(self):
        assert Kicker.has_kicker(["Kicker"])

    def test_from_oracle_text_true(self):
        assert Kicker.from_oracle_text("Kicker {2}{R}")

    def test_from_oracle_text_with_dash(self):
        assert Kicker.from_oracle_text("Kicker—{1}{B}")

    def test_from_oracle_text_false(self):
        assert not Kicker.from_oracle_text("Flying.")

    def test_from_oracle_text_empty(self):
        assert not Kicker.from_oracle_text("")

    def test_parse_kicker_cost(self):
        assert Kicker.parse_kicker_cost("Kicker {2}{R}") == "{2}{R}"

    def test_parse_kicker_cost_with_dash(self):
        assert Kicker.parse_kicker_cost("Kicker—{1}{B}") == "{1}{B}"

    def test_parse_kicker_cost_missing(self):
        assert Kicker.parse_kicker_cost("Flying.") is None

    def test_from_oracle_creates_instance(self):
        kw = Kicker.from_oracle("Kicker {3}")
        assert kw is not None
        assert kw.cost == "{3}"

    def test_from_oracle_missing(self):
        assert Kicker.from_oracle("Flying.") is None

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Sorcery", keywords=["kicker"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Kicker()
        assert kw.applies(gs, perm) is True
