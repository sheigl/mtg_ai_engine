from mtg_engine.models.game import GameState, PlayerState
from mtg_engine.ability.keywords.infect import (
    InfectKeyword, WitherKeyword, PoisonousKeyword,
)


class TestInfectKeyword:
    def test_has_infect_true(self):
        assert InfectKeyword.has_infect(["infect", "haste"])

    def test_has_infect_false(self):
        assert not InfectKeyword.has_infect(["haste", "trample"])

    def test_from_oracle_text_true(self):
        assert InfectKeyword.from_oracle_text("Has infect. Deals damage to creatures as -1/-1 counters.")

    def test_from_oracle_text_false(self):
        assert not InfectKeyword.from_oracle_text("Deals 2 damage to target creature.")

    def test_from_oracle_text_empty(self):
        assert not InfectKeyword.from_oracle_text("")


class TestWitherKeyword:
    def test_has_wither_true(self):
        assert WitherKeyword.has_wither(["wither", "haste"])

    def test_has_wither_false(self):
        assert not WitherKeyword.has_wither(["haste", "trample"])

    def test_from_oracle_text_true(self):
        assert WitherKeyword.from_oracle_text("Has wither. Deals damage to creatures as -1/-1 counters.")

    def test_from_oracle_text_false(self):
        assert not WitherKeyword.from_oracle_text("Deals 2 damage to target creature.")


class TestPoisonousKeyword:
    def test_parse_poisonous_1(self):
        keyword = PoisonousKeyword.from_oracle_text("Poisonous 1")
        assert keyword is not None
        assert keyword.poison_amount == 1

    def test_parse_poisonous_3(self):
        keyword = PoisonousKeyword.from_oracle_text("Poisonous 3")
        assert keyword is not None
        assert keyword.poison_amount == 3

    def test_parse_no_poisonous(self):
        keyword = PoisonousKeyword.from_oracle_text("Haste")
        assert keyword is None

    def test_parse_empty(self):
        keyword = PoisonousKeyword.from_oracle_text("")
        assert keyword is None

    def test_apply_poisonous(self):
        gs = GameState(
            game_id="test",
            seed=42,
            players=[PlayerState(name="P1", life=20, library=[], hand=[]),
                     PlayerState(name="P2", life=20, library=[], hand=[])],
            active_player="P1",
            priority_holder="P1",
        )
        keyword = PoisonousKeyword(poison_amount=2)
        gs2 = keyword.apply(gs, "source_id", "P2")
        assert gs2.players[1].poison_counters == 2
        # Original unchanged (pure transform)
        assert gs.players[1].poison_counters == 0

    def test_apply_poisonous_accumulates(self):
        gs = GameState(
            game_id="test",
            seed=42,
            players=[PlayerState(name="P1", life=20, library=[], hand=[]),
                     PlayerState(name="P2", life=20, library=[], hand=[])],
            active_player="P1",
            priority_holder="P1",
        )
        keyword = PoisonousKeyword(poison_amount=2)
        gs = keyword.apply(gs, "source_id", "P2")
        gs = keyword.apply(gs, "source_id", "P2")
        assert gs.players[1].poison_counters == 4

    def test_apply_poisonous_lethal(self):
        gs = GameState(
            game_id="test",
            seed=42,
            players=[PlayerState(name="P1", life=20, library=[], hand=[]),
                     PlayerState(name="P2", life=20, library=[], hand=[])],
            active_player="P1",
            priority_holder="P1",
        )
        gs.players[1].poison_counters = 7
        keyword = PoisonousKeyword(poison_amount=3)
        gs2 = keyword.apply(gs, "source_id", "P2")
        assert gs2.players[1].poison_counters == 10
        assert gs2.players[1].has_lost

    def test_apply_poisonous_pure_transform(self):
        """PoisonousKeyword.apply returns new GameState, doesn't mutate original."""
        gs = GameState(
            game_id="test",
            seed=42,
            players=[PlayerState(name="P1", life=20, library=[], hand=[]),
                     PlayerState(name="P2", life=20, library=[], hand=[])],
            active_player="P1",
            priority_holder="P1",
        )
        keyword = PoisonousKeyword(poison_amount=5)
        gs2 = keyword.apply(gs, "source_id", "P2")
        assert id(gs) != id(gs2)
        assert gs.players[1].poison_counters == 0  # Original unchanged
        assert gs2.players[1].poison_counters == 5
