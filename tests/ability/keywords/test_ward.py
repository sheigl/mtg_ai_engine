from mtg_engine.ability.keywords.ward import Ward


class TestWardKeyword:
    def test_has_ward_true(self):
        assert Ward.has_ward(["ward"])

    def test_has_ward_false(self):
        assert not Ward.has_ward(["flying", "haste"])

    def test_has_ward_case_insensitive(self):
        assert Ward.has_ward(["Ward"])

    def test_from_oracle_text_true(self):
        assert Ward.from_oracle_text("Ward {2}")

    def test_from_oracle_text_with_dash(self):
        assert Ward.from_oracle_text("Ward—Pay {3}")

    def test_from_oracle_text_plain_number(self):
        assert Ward.from_oracle_text("Ward 2")

    def test_from_oracle_text_false(self):
        assert not Ward.from_oracle_text("Flying.")

    def test_from_oracle_text_empty(self):
        assert not Ward.from_oracle_text("")

    def test_parse_ward_cost_braces(self):
        assert Ward.parse_ward_cost("Ward {3}") == "{3}"

    def test_parse_ward_cost_with_dash(self):
        assert Ward.parse_ward_cost("Ward—Pay {2}{R}") == "{2}{R}"

    def test_parse_ward_cost_plain_number(self):
        assert Ward.parse_ward_cost("Ward 4") == "{4}"

    def test_parse_ward_cost_default(self):
        assert Ward.parse_ward_cost("Some other text") == "{2}"

    def test_parse_ward_cost_empty(self):
        assert Ward.parse_ward_cost("") == "{2}"

    def test_from_oracle_creates_instance(self):
        kw = Ward.from_oracle("Ward {4}")
        assert kw is not None
        assert kw.cost == "{4}"

    def test_from_oracle_missing(self):
        assert Ward.from_oracle("Flying.") is None

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Creature", keywords=["ward"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Ward()
        assert kw.applies(gs, perm) is True

    def test_applies_from_oracle(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Creature", oracle_text="Ward {2}", keywords=[])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Ward()
        assert kw.applies(gs, perm) is True
