from mtg_engine.ability.keywords.ninjutsu import Ninjutsu


class TestNinjutsuKeyword:
    def test_has_ninjutsu_true(self):
        assert Ninjutsu.has_ninjutsu(["ninjutsu"])

    def test_has_ninjutsu_false(self):
        assert not Ninjutsu.has_ninjutsu(["flying", "haste"])

    def test_has_ninjutsu_case_insensitive(self):
        assert Ninjutsu.has_ninjutsu(["Ninjutsu"])

    def test_from_oracle_text_true(self):
        assert Ninjutsu.from_oracle_text("Ninjutsu {2}{U}")

    def test_from_oracle_text_with_dash(self):
        assert Ninjutsu.from_oracle_text("Ninjutsu—{1}{B}")

    def test_from_oracle_text_false(self):
        assert not Ninjutsu.from_oracle_text("Flying.")

    def test_from_oracle_text_empty(self):
        assert not Ninjutsu.from_oracle_text("")

    def test_parse_ninjutsu_cost(self):
        assert Ninjutsu.parse_ninjutsu_cost("Ninjutsu {2}{U}") == "{2}{U}"

    def test_parse_ninjutsu_cost_with_dash(self):
        assert Ninjutsu.parse_ninjutsu_cost("Ninjutsu—{1}{B}") == "{1}{B}"

    def test_parse_ninjutsu_cost_missing(self):
        assert Ninjutsu.parse_ninjutsu_cost("Flying.") is None

    def test_from_oracle_creates_instance(self):
        kw = Ninjutsu.from_oracle("Ninjutsu {3}{U}")
        assert kw is not None
        assert kw.cost == "{3}{U}"

    def test_from_oracle_missing(self):
        assert Ninjutsu.from_oracle("Flying.") is None

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Creature", keywords=["ninjutsu"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Ninjutsu()
        assert kw.applies(gs, perm) is True
