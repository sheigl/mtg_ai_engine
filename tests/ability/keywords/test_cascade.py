from mtg_engine.ability.keywords.cascade import Cascade


class TestCascadeKeyword:
    def test_has_cascade_true(self):
        assert Cascade.has_cascade(["cascade", "flying"])

    def test_has_cascade_false(self):
        assert not Cascade.has_cascade(["flying", "haste"])

    def test_has_cascade_case_insensitive(self):
        assert Cascade.has_cascade(["Cascade"])

    def test_from_oracle_text_true(self):
        assert Cascade.from_oracle_text("Cascade (When you cast this spell, exile cards from the top...")

    def test_from_oracle_text_false(self):
        assert not Cascade.from_oracle_text("Flying. Trample.")

    def test_from_oracle_text_empty(self):
        assert not Cascade.from_oracle_text("")

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Sorcery", keywords=["cascade"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Cascade()
        assert kw.applies(gs, perm) is True

    def test_applies_from_oracle(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Sorcery", oracle_text="Cascade", keywords=[])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Cascade()
        assert kw.applies(gs, perm) is True
