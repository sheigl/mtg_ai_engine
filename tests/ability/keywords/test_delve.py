from mtg_engine.ability.keywords.delve import Delve


class TestDelveKeyword:
    def test_has_delve_true(self):
        assert Delve.has_delve(["delve"])

    def test_has_delve_false(self):
        assert not Delve.has_delve(["flying", "trample"])

    def test_has_delve_case_insensitive(self):
        assert Delve.has_delve(["Delve"])

    def test_from_oracle_text_true(self):
        assert Delve.from_oracle_text("Delve (Each card you exile from your graveyard while casting pays for {1}.)")

    def test_from_oracle_text_false(self):
        assert not Delve.from_oracle_text("Flying.")

    def test_from_oracle_text_empty(self):
        assert not Delve.from_oracle_text("")

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Sorcery", keywords=["delve"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Delve()
        assert kw.applies(gs, perm) is True

    def test_applies_from_oracle(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Sorcery", oracle_text="Delve", keywords=[])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Delve()
        assert kw.applies(gs, perm) is True
