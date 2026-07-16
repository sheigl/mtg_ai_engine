from mtg_engine.ability.keywords.escape import Escape


class TestEscapeKeyword:
    def test_has_escape_true(self):
        assert Escape.has_escape(["escape"])

    def test_has_escape_false(self):
        assert not Escape.has_escape(["flying", "haste"])

    def test_has_escape_case_insensitive(self):
        assert Escape.has_escape(["Escape"])

    def test_from_oracle_text_true(self):
        assert Escape.from_oracle_text("Escape—{3}{G}{G}, Exile five other cards from your graveyard.")

    def test_from_oracle_text_false(self):
        assert not Escape.from_oracle_text("Flying.")

    def test_from_oracle_text_empty(self):
        assert not Escape.from_oracle_text("")

    def test_parse_escape_cost(self):
        assert Escape.parse_escape_cost("Escape—{3}{G}{G}, Exile five other cards from your graveyard.") == "{3}{G}{G}"

    def test_parse_escape_cost_missing(self):
        assert Escape.parse_escape_cost("Flying.") is None

    def test_parse_exile_count(self):
        assert Escape.parse_exile_count("Escape—{2}{R}, Exile three other cards from your graveyard.") == 3

    def test_parse_exile_count_five(self):
        assert Escape.parse_exile_count("Escape—{4}{B}, Exile five other cards from your graveyard.") == 5

    def test_parse_exile_count_none(self):
        assert Escape.parse_exile_count("Escape—{2}{R}") == 0

    def test_parse_exile_count_empty(self):
        assert Escape.parse_exile_count("") == 0

    def test_from_oracle_creates_instance(self):
        kw = Escape.from_oracle("Escape—{3}{G}{G}, Exile five other cards from your graveyard.")
        assert kw is not None
        assert kw.cost == "{3}{G}{G}"
        assert kw.exile_count == 5

    def test_from_oracle_missing(self):
        assert Escape.from_oracle("Flying.") is None

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Creature", keywords=["escape"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Escape()
        assert kw.applies(gs, perm) is True
