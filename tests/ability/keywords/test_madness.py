from mtg_engine.ability.keywords.madness import Madness


class TestMadnessKeyword:
    def test_has_madness_true(self):
        assert Madness.has_madness(["madness"])

    def test_has_madness_false(self):
        assert not Madness.has_madness(["flying", "haste"])

    def test_has_madness_case_insensitive(self):
        assert Madness.has_madness(["Madness"])

    def test_from_oracle_text_true(self):
        assert Madness.from_oracle_text("Madness {2}{B}")

    def test_from_oracle_text_with_dash(self):
        assert Madness.from_oracle_text("Madness—{1}{R}")

    def test_from_oracle_text_false(self):
        assert not Madness.from_oracle_text("Flying.")

    def test_from_oracle_text_empty(self):
        assert not Madness.from_oracle_text("")

    def test_parse_madness_cost(self):
        assert Madness.parse_madness_cost("Madness {2}{B}") == "{2}{B}"

    def test_parse_madness_cost_with_dash(self):
        assert Madness.parse_madness_cost("Madness—{1}{R}") == "{1}{R}"

    def test_parse_madness_cost_missing(self):
        assert Madness.parse_madness_cost("Flying.") is None

    def test_from_oracle_creates_instance(self):
        kw = Madness.from_oracle("Madness {B}")
        assert kw is not None
        assert kw.cost == "{B}"

    def test_from_oracle_missing(self):
        assert Madness.from_oracle("Flying.") is None

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Instant", keywords=["madness"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Madness()
        assert kw.applies(gs, perm) is True
