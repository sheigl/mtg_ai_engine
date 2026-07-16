from mtg_engine.models.game import Card, Permanent
from mtg_engine.ability.keywords.reach import Reach


class TestReachKeyword:
    def test_has_reach_true(self):
        assert Reach.has_reach(["reach", "haste"])

    def test_has_reach_false(self):
        assert not Reach.has_reach(["haste", "trample"])

    def test_has_reach_case_insensitive(self):
        assert Reach.has_reach(["Reach"])

    def test_from_oracle_text_true(self):
        assert Reach.from_oracle_text("This creature has reach.")

    def test_from_oracle_text_false(self):
        assert not Reach.from_oracle_text("Deals 2 damage.")

    def test_from_oracle_text_empty(self):
        assert not Reach.from_oracle_text("")

    def test_can_block_flying_with_reach(self):
        """CR 702.160b: Reach can block flying."""
        assert Reach.can_block_flying(["reach"])

    def test_can_block_flying_with_flying(self):
        """Flying can also block flying."""
        assert Reach.can_block_flying(["flying"])

    def test_can_block_flying_with_both(self):
        assert Reach.can_block_flying(["reach", "flying"])

    def test_cannot_block_flying_without_either(self):
        """CR 702.9b: Without flying or reach, can't block flying."""
        assert not Reach.can_block_flying(["haste"])

    def test_cannot_block_flying_empty_keywords(self):
        assert not Reach.can_block_flying([])


class TestReachBlockingIntegration:
    """Integration tests for reach in blocking rules."""

    def _make_perm(self, name: str, controller: str, keywords: list[str]) -> Permanent:
        return Permanent(
            id=f"perm_{name}",
            card=Card(name=name, type_line="Creature", keywords=keywords),
            controller=controller,
            tapped=False,
        )

    def test_reach_blocks_flying_legal(self):
        """Reach creature can legally block flying creature."""
        blocker = self._make_perm("Wall", "P2", ["reach"])
        assert Reach.can_block_flying(blocker.card.keywords)

    def test_no_reach_no_flying_cannot_block(self):
        """Creature without reach or flying cannot block flying."""
        blocker = self._make_perm("Goblin", "P2", ["haste"])
        assert not Reach.can_block_flying(blocker.card.keywords)
