from mtg_engine.ability.keywords.dash import Dash


class TestDashKeyword:
    def test_has_dash_true(self):
        assert Dash.has_dash(["dash"])

    def test_has_dash_false(self):
        assert not Dash.has_dash(["flying", "haste"])

    def test_has_dash_case_insensitive(self):
        assert Dash.has_dash(["Dash"])

    def test_from_oracle_text_true(self):
        assert Dash.from_oracle_text("Dash {1}{R}")

    def test_from_oracle_text_with_dash(self):
        assert Dash.from_oracle_text("Dash—{2}{R}")

    def test_from_oracle_text_false(self):
        assert not Dash.from_oracle_text("Flying.")

    def test_from_oracle_text_empty(self):
        assert not Dash.from_oracle_text("")

    def test_parse_dash_cost(self):
        assert Dash.parse_dash_cost("Dash {1}{R}") == "{1}{R}"

    def test_parse_dash_cost_with_dash(self):
        assert Dash.parse_dash_cost("Dash—{2}{R}") == "{2}{R}"

    def test_parse_dash_cost_missing(self):
        assert Dash.parse_dash_cost("Flying.") is None

    def test_from_oracle_creates_instance(self):
        kw = Dash.from_oracle("Dash {R}")
        assert kw is not None
        assert kw.cost == "{R}"

    def test_from_oracle_missing(self):
        assert Dash.from_oracle("Flying.") is None

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Creature", keywords=["dash"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Dash()
        assert kw.applies(gs, perm) is True
