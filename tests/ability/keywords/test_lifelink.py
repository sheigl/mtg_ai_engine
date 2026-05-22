import pytest
from mtg_engine.models.game import Card, GameState, PlayerState, Permanent
from mtg_engine.ability.keywords.lifelink import Lifelink


class TestLifelinkKeyword:
    def test_has_lifelink_true(self):
        assert Lifelink.has_lifelink(["lifelink", "haste"])

    def test_has_lifelink_false(self):
        assert not Lifelink.has_lifelink(["haste", "trample"])

    def test_has_lifelink_case_insensitive(self):
        assert Lifelink.has_lifelink(["Lifelink"])

    def test_from_oracle_text_true(self):
        assert Lifelink.from_oracle_text("White Knight has lifelink.")

    def test_from_oracle_text_false(self):
        assert not Lifelink.from_oracle_text("Deals 2 damage to target creature.")

    def test_from_oracle_text_empty(self):
        assert not Lifelink.from_oracle_text("")

    def test_apply_lifelink_gain(self):
        result = Lifelink.apply_lifelink_gain(20, 5)
        assert result == 25

    def test_apply_lifelink_zero_damage(self):
        result = Lifelink.apply_lifelink_gain(20, 0)
        assert result == 20


class TestLifelinkCombat:
    """Integration tests for lifelink in combat damage."""

    def _make_perm(self, name: str, controller: str, keywords: list[str]) -> Permanent:
        return Permanent(
            id=f"perm_{name}",
            card=Card(name=name, type_line="Creature", keywords=keywords),
            controller=controller,
            tapped=False,
        )

    def test_lifelink_gains_life_on_damage(self):
        """CR 702.15b: Source controller gains life equal to damage dealt."""
        attacker = self._make_perm("Angel", "P1", ["lifelink"])
        blocker = self._make_perm("Goblin", "P2", [])

        gs = GameState(
            game_id="test",
            seed=42,
            players=[
                PlayerState(name="P1", life=15),
                PlayerState(name="P2", life=20),
            ],
            active_player="P1",
            priority_holder="P1",
            battlefield=[attacker, blocker],
        )

        attacker.card.power = "3"
        from mtg_engine.engine.combat.core import _effective_power, _has_keyword
        power = _effective_power(attacker)
        has_ll = _has_keyword(attacker, "lifelink")
        assert has_ll
        new_life = Lifelink.apply_lifelink_gain(gs.players[0].life, power)
        assert new_life == 18  # 15 + 3

    def test_no_lifelink_no_gain(self):
        """Creature without lifelink doesn't gain life."""
        attacker = self._make_perm("Wolf", "P1", ["haste"])
        assert not Lifelink.has_lifelink(attacker.card.keywords)
