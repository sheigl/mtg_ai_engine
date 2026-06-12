from mtg_engine.models.game import Card, Permanent
from mtg_engine.ability.keywords.hexproof import Hexproof


class TestHexproofKeyword:
    def test_has_hexproof_true(self):
        assert Hexproof.has_hexproof(["hexproof", "flying"])

    def test_has_hexproof_false(self):
        assert not Hexproof.has_hexproof(["flying", "haste"])

    def test_has_hexproof_case_insensitive(self):
        assert Hexproof.has_hexproof(["Hexproof"])

    def test_from_oracle_text_true(self):
        assert Hexproof.from_oracle_text("This creature has hexproof.")

    def test_from_oracle_text_false(self):
        assert not Hexproof.from_oracle_text("Deals 2 damage.")

    def test_from_oracle_text_empty(self):
        assert not Hexproof.from_oracle_text("")

    def test_can_be_targeted_by_owner(self):
        """CR 702.15b: Owner can target their own hexproof permanent."""
        assert Hexproof.can_be_targeted(["hexproof"], "P1", "P1")

    def test_cannot_be_targeted_by_opponent(self):
        """CR 702.15b: Opponent cannot target your hexproof permanent."""
        assert not Hexproof.can_be_targeted(["hexproof"], "P2", "P1")

    def test_can_target_non_hexproof_anyone(self):
        """Non-hexproof permanents can be targeted by anyone."""
        assert Hexproof.can_be_targeted(["flying"], "P2", "P1")

    def test_can_target_empty_keywords_anyone(self):
        assert Hexproof.can_be_targeted([], "P2", "P1")


class TestHexproofTargetingIntegration:
    """Integration tests for hexproof in targeting rules."""

    def _make_perm(self, name: str, controller: str, keywords: list[str]) -> Permanent:
        return Permanent(
            id=f"perm_{name}",
            card=Card(name=name, type_line="Creature", keywords=keywords),
            controller=controller,
            tapped=False,
        )

    def test_hexproof_blocks_opponent_spell(self):
        """Opponent's spell targeting hexproof permanent is illegal."""
        target = self._make_perm("Angel", "P1", ["hexproof", "flying"])
        assert not Hexproof.can_be_targeted(target.card.keywords, "P2", "P1")

    def test_hexproof_allows_own_burst(self):
        """Owner's spell targeting own hexproof permanent is legal."""
        target = self._make_perm("Angel", "P1", ["hexproof", "flying"])
        assert Hexproof.can_be_targeted(target.card.keywords, "P1", "P1")

    def test_no_hexproof_anyone_targets(self):
        target = self._make_perm("Wolf", "P1", ["haste"])
        assert Hexproof.can_be_targeted(target.card.keywords, "P2", "P1")
