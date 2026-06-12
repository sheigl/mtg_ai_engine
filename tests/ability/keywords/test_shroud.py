from mtg_engine.models.game import Card, Permanent
from mtg_engine.ability.keywords.shroud import Shroud


class TestShroudKeyword:
    def test_has_shroud_true(self):
        assert Shroud.has_shroud(["shroud", "flying"])

    def test_has_shroud_false(self):
        assert not Shroud.has_shroud(["flying", "haste"])

    def test_has_shroud_case_insensitive(self):
        assert Shroud.has_shroud(["Shroud"])

    def test_from_oracle_text_true(self):
        assert Shroud.from_oracle_text("This creature has shroud.")

    def test_from_oracle_text_false(self):
        assert not Shroud.from_oracle_text("Deals 2 damage.")

    def test_from_oracle_text_empty(self):
        assert not Shroud.from_oracle_text("")

    def test_cannot_be_targeted_by_anyone(self):
        """CR 702.36b: Shrouded permanent can't be targeted by anyone."""
        assert not Shroud.can_be_targeted(["shroud"])

    def test_can_target_non_shrouded(self):
        """Non-shrouded permanents can be targeted."""
        assert Shroud.can_be_targeted(["flying"])

    def test_can_target_empty_keywords(self):
        assert Shroud.can_be_targeted([])


class TestShroudTargetingIntegration:
    """Integration tests for shroud in targeting rules."""

    def _make_perm(self, name: str, controller: str, keywords: list[str]) -> Permanent:
        return Permanent(
            id=f"perm_{name}",
            card=Card(name=name, type_line="Creature", keywords=keywords),
            controller=controller,
            tapped=False,
        )

    def test_shroud_blocks_own_targeting(self):
        """CR 702.36b: Even owner can't target shrouded permanent."""
        target = self._make_perm("AncientOne", "P1", ["shroud"])
        assert not Shroud.can_be_targeted(target.card.keywords)

    def test_shroud_blocks_opponent_targeting(self):
        """Opponent also can't target shrouded permanent."""
        target = self._make_perm("AncientOne", "P1", ["shroud"])
        assert not Shroud.can_be_targeted(target.card.keywords)

    def test_no_shroud_can_target(self):
        target = self._make_perm("Wolf", "P1", ["haste"])
        assert Shroud.can_be_targeted(target.card.keywords)

    def test_shroud_vs_hexproof_distinction(self):
        """Shroud blocks everyone; hexproof only blocks opponents."""
        from mtg_engine.ability.keywords.hexproof import Hexproof
        shrouded_kws = ["shroud"]
        hexproof_kws = ["hexproof"]
        # Shroud: nobody can target
        assert not Shroud.can_be_targeted(shrouded_kws)
        # Hexproof: owner can target, opponent can't
        assert Hexproof.can_be_targeted(hexproof_kws, "P1", "P1")
        assert not Hexproof.can_be_targeted(hexproof_kws, "P2", "P1")
