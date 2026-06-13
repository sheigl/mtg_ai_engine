from mtg_engine.ability.keywords.convoke import Convoke


class TestConvokeKeyword:
    def test_has_convoke_true(self):
        assert Convoke.has_convoke(["convoke"])

    def test_has_convoke_false(self):
        assert not Convoke.has_convoke(["flying", "haste"])

    def test_has_convoke_case_insensitive(self):
        assert Convoke.has_convoke(["Convoke"])

    def test_from_oracle_text_true(self):
        assert Convoke.from_oracle_text("Convoke (Your creatures can help cast this spell.)")

    def test_from_oracle_text_false(self):
        assert not Convoke.from_oracle_text("Flying.")

    def test_from_oracle_text_empty(self):
        assert not Convoke.from_oracle_text("")

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Sorcery", keywords=["convoke"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Convoke()
        assert kw.applies(gs, perm) is True

    def test_applies_from_oracle(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Sorcery", oracle_text="Convoke", keywords=[])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Convoke()
        assert kw.applies(gs, perm) is True
