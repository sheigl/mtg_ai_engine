import pytest
from mtg_engine.models.game import Card, GameState, PlayerState, Permanent
from mtg_engine.ability.keywords.menace import Menace


class TestMenaceKeyword:
    def test_has_menace_true(self):
        assert Menace.has_menace(["menace", "haste"])

    def test_has_menace_false(self):
        assert not Menace.has_menace(["haste", "trample"])

    def test_has_menace_case_insensitive(self):
        assert Menace.has_menace(["Menace"])

    def test_from_oracle_text_true(self):
        assert Menace.from_oracle_text("This creature has menace.")

    def test_from_oracle_text_false(self):
        assert not Menace.from_oracle_text("Deals 2 damage.")

    def test_from_oracle_text_empty(self):
        assert not Menace.from_oracle_text("")

    def test_min_blockers(self):
        """CR 702.45b: Menace requires at least 2 blockers."""
        assert Menace.min_blockers() == 2

    def test_is_block_legal_no_menace_any_count(self):
        """Without menace, any number of blockers is legal."""
        assert Menace.is_block_legal([], 0)
        assert Menace.is_block_legal(["haste"], 1)
        assert Menace.is_block_legal(["trample"], 3)

    def test_is_block_legal_menace_two_blockers(self):
        """Menace with exactly 2 blockers is legal."""
        assert Menace.is_block_legal(["menace"], 2)

    def test_is_block_legal_menace_three_blockers(self):
        """Menace with 3+ blockers is legal."""
        assert Menace.is_block_legal(["menace"], 3)

    def test_is_block_legal_menace_one_blocker_illegal(self):
        """Menace with only 1 blocker is illegal."""
        assert not Menace.is_block_legal(["menace"], 1)

    def test_is_block_legal_menace_zero_blockers_illegal(self):
        """Menace with 0 blockers in a block declaration is illegal."""
        assert not Menace.is_block_legal(["menace"], 0)


class TestMenaceBlockingIntegration:
    """Integration tests for menace in blocking rules."""

    def _make_perm(self, name: str, controller: str, keywords: list[str]) -> Permanent:
        return Permanent(
            id=f"perm_{name}",
            card=Card(name=name, type_line="Creature", keywords=keywords),
            controller=controller,
            tapped=False,
        )

    def test_menace_requires_two_blockers(self):
        """Attacker with menace must have 2+ blockers."""
        attacker = self._make_perm("BigCreature", "P1", ["menace"])
        assert Menace.has_menace(attacker.card.keywords)
        assert Menace.min_blockers() == 2
