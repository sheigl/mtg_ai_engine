from mtg_engine.ability.keywords.flashback import Flashback


class TestFlashbackKeyword:
    def test_has_flashback_true(self):
        assert Flashback.has_flashback(["flashback"])

    def test_has_flashback_false(self):
        assert not Flashback.has_flashback(["flying", "haste"])

    def test_has_flashback_case_insensitive(self):
        assert Flashback.has_flashback(["Flashback"])

    def test_from_oracle_text_true(self):
        assert Flashback.from_oracle_text("Flashback {2}{U}")

    def test_from_oracle_text_with_dash(self):
        assert Flashback.from_oracle_text("Flashback—{3}{G}")

    def test_from_oracle_text_false(self):
        assert not Flashback.from_oracle_text("Flying.")

    def test_from_oracle_text_empty(self):
        assert not Flashback.from_oracle_text("")

    def test_parse_flashback_cost(self):
        assert Flashback.parse_flashback_cost("Flashback {2}{R}") == "{2}{R}"

    def test_parse_flashback_cost_with_dash(self):
        assert Flashback.parse_flashback_cost("Flashback—{1}{W}") == "{1}{W}"

    def test_parse_flashback_cost_missing(self):
        assert Flashback.parse_flashback_cost("Flying.") is None

    def test_from_oracle_creates_instance(self):
        kw = Flashback.from_oracle("Flashback {2}{B}")
        assert kw is not None
        assert kw.cost == "{2}{B}"

    def test_from_oracle_missing(self):
        assert Flashback.from_oracle("Flying.") is None

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Instant", keywords=["flashback"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Flashback()
        assert kw.applies(gs, perm) is True
