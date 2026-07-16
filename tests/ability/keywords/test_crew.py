from mtg_engine.ability.keywords.crew import Crew


class TestCrewKeyword:
    def test_has_crew_true(self):
        assert Crew.has_crew(["crew"])

    def test_has_crew_false(self):
        assert not Crew.has_crew(["flying", "haste"])

    def test_has_crew_case_insensitive(self):
        assert Crew.has_crew(["Crew"])

    def test_from_oracle_text_true(self):
        assert Crew.from_oracle_text("Crew 3")

    def test_from_oracle_text_false(self):
        assert not Crew.from_oracle_text("Flying.")

    def test_from_oracle_text_empty(self):
        assert not Crew.from_oracle_text("")

    def test_parse_crew_value(self):
        assert Crew.parse_crew_value("Crew 4") == 4

    def test_parse_crew_value_default(self):
        assert Crew.parse_crew_value("Flying.") == 1

    def test_parse_crew_value_empty(self):
        assert Crew.parse_crew_value("") == 1

    def test_from_oracle_creates_instance(self):
        kw = Crew.from_oracle("Crew 5")
        assert kw is not None
        assert kw.value == 5

    def test_from_oracle_missing(self):
        assert Crew.from_oracle("Flying.") is None

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Artifact — Vehicle", keywords=["crew"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Crew()
        assert kw.applies(gs, perm) is True

    def test_applies_from_oracle(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Artifact — Vehicle", oracle_text="Crew 3", keywords=[])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Crew()
        assert kw.applies(gs, perm) is True
