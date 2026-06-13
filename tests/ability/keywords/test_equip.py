from mtg_engine.ability.keywords.equip import Equip


class TestEquipKeyword:
    def test_has_equip_true(self):
        assert Equip.has_equip(["equip"])

    def test_has_equip_false(self):
        assert not Equip.has_equip(["flying", "haste"])

    def test_has_equip_case_insensitive(self):
        assert Equip.has_equip(["Equip"])

    def test_from_oracle_text_true(self):
        assert Equip.from_oracle_text("Equip {3}")

    def test_from_oracle_text_with_dash(self):
        assert Equip.from_oracle_text("Equip—{2}{R}")

    def test_from_oracle_text_false(self):
        assert not Equip.from_oracle_text("Flying.")

    def test_from_oracle_text_empty(self):
        assert not Equip.from_oracle_text("")

    def test_parse_equip_cost(self):
        assert Equip.parse_equip_cost("Equip {2}") == "{2}"

    def test_parse_equip_cost_with_dash(self):
        assert Equip.parse_equip_cost("Equip—{4}") == "{4}"

    def test_parse_equip_cost_missing(self):
        assert Equip.parse_equip_cost("Flying.") is None

    def test_from_oracle_creates_instance(self):
        kw = Equip.from_oracle("Equip {2}")
        assert kw is not None
        assert kw.cost == "{2}"

    def test_from_oracle_missing(self):
        assert Equip.from_oracle("Flying.") is None

    def test_applies_from_keywords(self):
        from mtg_engine.models.game import Card, Permanent, GameState, Phase, Step, PlayerState
        card = Card(name="Test", type_line="Artifact — Equipment", keywords=["equip"])
        perm = Permanent(card=card, controller="p1")
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[PlayerState(name="p1")],
        )
        kw = Equip()
        assert kw.applies(gs, perm) is True
