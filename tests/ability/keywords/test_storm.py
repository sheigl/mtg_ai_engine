from mtg_engine.ability.keywords.storm import Storm


class TestStormKeyword:
    def test_has_storm_true(self):
        assert Storm.has_storm(["storm", "flying"])

    def test_has_storm_false(self):
        assert not Storm.has_storm(["flying", "haste"])

    def test_has_storm_case_insensitive(self):
        assert Storm.has_storm(["Storm"])

    def test_from_oracle_text_true(self):
        assert Storm.from_oracle_text("Storm (When you cast this spell, copy it for each spell cast before it this turn.)")

    def test_from_oracle_text_false(self):
        assert not Storm.from_oracle_text("Flying. Trample.")

    def test_from_oracle_text_empty(self):
        assert not Storm.from_oracle_text("")

    def test_storm_count_default(self):
        class FakeGS:
            spells_cast_this_turn = 3
        assert Storm.get_storm_count(FakeGS()) == 3

    def test_storm_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Instant", keywords=["storm"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Storm()
        assert kw.applies(gs, perm) is True

    def test_storm_applies_from_oracle(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Instant", oracle_text="Storm", keywords=[])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Storm()
        assert kw.applies(gs, perm) is True
