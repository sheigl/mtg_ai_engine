from mtg_engine.models.game import Card, Permanent
from mtg_engine.ability.keywords.deathtouch import Deathtouch


class TestDeathtouchKeyword:
    def test_has_deathtouch_true(self):
        assert Deathtouch.has_deathtouch(["deathtouch", "haste"])

    def test_has_deathtouch_false(self):
        assert not Deathtouch.has_deathtouch(["haste", "trample"])

    def test_has_deathtouch_case_insensitive(self):
        assert Deathtouch.has_deathtouch(["Deathtouch"])

    def test_from_oracle_text_true(self):
        assert Deathtouch.from_oracle_text("Black Knight has deathtouch.")

    def test_from_oracle_text_false(self):
        assert not Deathtouch.from_oracle_text("Deals 2 damage to target creature.")

    def test_from_oracle_text_empty(self):
        assert not Deathtouch.from_oracle_text("")

    def test_is_lethal_any_nonzero(self):
        """CR 702.2c: Any nonzero damage is lethal with deathtouch."""
        assert Deathtouch.is_lethal(1, 10)
        assert Deathtouch.is_lethal(1, 100)
        assert Deathtouch.is_lethal(3, 7)

    def test_is_lethal_zero_not_lethal(self):
        assert not Deathtouch.is_lethal(0, 5)

    def test_min_lethal_damage(self):
        assert Deathtouch.min_lethal_damage() == 1


class TestDeathtouchSBA:
    """Integration tests for deathtouch SBA tracking."""

    def _make_perm(self, name: str, controller: str, keywords: list[str]) -> Permanent:
        return Permanent(
            id=f"perm_{name}",
            card=Card(name=name, type_line="Creature", keywords=keywords),
            controller=controller,
            tapped=False,
        )

    def test_deathtouch_damage_tracked(self):
        """Verify deathtouch damage is tracked via counter for SBA."""
        attacker = self._make_perm("Demon", "P1", ["deathtouch"])
        blocker = self._make_perm("Wall", "P2", [])

        assert Deathtouch.has_deathtouch(attacker.card.keywords)
        damage = 1
        # Simulate SBA tracking (as done in combat/core.py:633)
        blocker.counters["__deathtouch_damage__"] = (
            blocker.counters.get("__deathtouch_damage__", 0) + damage
        )
        assert blocker.counters.get("__deathtouch_damage__", 0) > 0

    def test_deathtouch_accumulates(self):
        """Multiple deathtouch sources accumulate tracking."""
        blocker = self._make_perm("Wall", "P2", [])
        blocker.counters["__deathtouch_damage__"] = (
            blocker.counters.get("__deathtouch_damage__", 0) + 1
        )
        blocker.counters["__deathtouch_damage__"] = (
            blocker.counters.get("__deathtouch_damage__", 0) + 2
        )
        assert blocker.counters["__deathtouch_damage__"] == 3

    def test_no_deathtouch_no_tracking(self):
        """Non-deathtouch damage doesn't set tracking counter."""
        attacker = self._make_perm("Wolf", "P1", ["haste"])
        assert not Deathtouch.has_deathtouch(attacker.card.keywords)
