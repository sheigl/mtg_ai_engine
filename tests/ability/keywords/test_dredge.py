from mtg_engine.ability.keywords.dredge import Dredge


class TestDredgeKeyword:
    def test_has_dredge_true(self):
        assert Dredge.has_dredge(["dredge"])

    def test_has_dredge_false(self):
        assert not Dredge.has_dredge(["flying", "haste"])

    def test_has_dredge_case_insensitive(self):
        assert Dredge.has_dredge(["Dredge"])

    def test_from_oracle_text_true(self):
        assert Dredge.from_oracle_text("Dredge 5 (If you would draw a card, you may...")

    def test_from_oracle_text_false(self):
        assert not Dredge.from_oracle_text("Flying.")

    def test_from_oracle_text_empty(self):
        assert not Dredge.from_oracle_text("")

    def test_parse_dredge_value(self):
        assert Dredge.parse_dredge_value("Dredge 6") == 6

    def test_parse_dredge_value_default(self):
        assert Dredge.parse_dredge_value("Flying.") == 1

    def test_parse_dredge_value_empty(self):
        assert Dredge.parse_dredge_value("") == 1

    def test_from_oracle_creates_instance(self):
        kw = Dredge.from_oracle("Dredge 3")
        assert kw is not None
        assert kw.value == 3

    def test_from_oracle_missing(self):
        assert Dredge.from_oracle("Flying.") is None

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Enchantment", keywords=["dredge"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Dredge()
        assert kw.applies(gs, perm) is True

    def test_applies_from_oracle(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Enchantment", oracle_text="Dredge 5", keywords=[])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Dredge()
        assert kw.applies(gs, perm) is True
