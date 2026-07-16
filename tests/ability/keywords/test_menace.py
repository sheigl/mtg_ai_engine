from mtg_engine.models.game import Card, GameState, Phase, Step, PlayerState, Permanent
from mtg_engine.ability.keywords.menace import Menace, is_menacing, can_block_menacing


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


class TestMenaceQueryHelpers:
    """Integration tests for menace query helpers with GameState."""

    def _make_game(self) -> GameState:
        p1 = PlayerState(name="p1", life=20)
        p2 = PlayerState(name="p2", life=20)
        return GameState(
            game_id="test-menace-query",
            seed=1,
            active_player="p1",
            priority_holder="p1",
            phase=Phase.COMBAT,
            step=Step.DECLARE_BLOCKERS,
            players=[p1, p2],
        )

    def _make_perm(self, name: str, controller: str, keywords: list[str]) -> Permanent:
        return Permanent(
            id=f"perm_{name}",
            card=Card(name=name, type_line="Creature", keywords=keywords),
            controller=controller,
            tapped=False,
        )

    # --- is_menacing tests ---

    def test_is_menacing_true_on_battlefield(self):
        """is_menacing returns True for a menacing permanent on battlefield."""
        gs = self._make_game()
        perm = self._make_perm("MenaceBeast", "p1", ["menace"])
        gs.battlefield.append(perm)

        assert is_menacing(gs, perm.id) is True

    def test_is_menacing_false_no_keyword(self):
        """is_menacing returns False for a permanent without menace."""
        gs = self._make_game()
        perm = self._make_perm("Wolf", "p1", ["haste"])
        gs.battlefield.append(perm)

        assert is_menacing(gs, perm.id) is False

    def test_is_menacing_false_not_on_battlefield(self):
        """is_menacing returns False for a permanent not on battlefield."""
        gs = self._make_game()
        # Permanent exists but is NOT on battlefield
        self._make_perm("MenaceBeast", "p1", ["menace"])

        assert is_menacing(gs, "perm_MenaceBeast") is False

    def test_is_menacing_false_empty_battlefield(self):
        """is_menacing returns False when battlefield is empty."""
        gs = self._make_game()

        assert is_menacing(gs, "nonexistent") is False

    # --- can_block_menacing tests ---

    def test_can_block_no_menace_one_blocker_legal(self):
        """Non-menacing attacker can be blocked by 1 creature."""
        gs = self._make_game()
        attacker = self._make_perm("Wolf", "p1", ["haste"])
        blocker1 = self._make_perm("GuardDog", "p2", [])
        gs.battlefield.extend([attacker, blocker1])

        assert can_block_menacing(gs, attacker.id, [blocker1.id]) is True

    def test_can_block_no_menace_zero_blockers_legal(self):
        """Non-menacing attacker can be unblocked (0 blockers)."""
        gs = self._make_game()
        attacker = self._make_perm("Wolf", "p1", ["haste"])
        gs.battlefield.append(attacker)

        assert can_block_menacing(gs, attacker.id, []) is True

    def test_can_block_menace_two_blockers_legal(self):
        """Menacing attacker CAN be blocked by 2 creatures."""
        gs = self._make_game()
        attacker = self._make_perm("BigCreature", "p1", ["menace"])
        blocker1 = self._make_perm("GuardDog1", "p2", [])
        blocker2 = self._make_perm("GuardDog2", "p2", [])
        gs.battlefield.extend([attacker, blocker1, blocker2])

        assert can_block_menacing(gs, attacker.id, [blocker1.id, blocker2.id]) is True

    def test_can_block_menace_three_blockers_legal(self):
        """Menacing attacker CAN be blocked by 3+ creatures."""
        gs = self._make_game()
        attacker = self._make_perm("BigCreature", "p1", ["menace"])
        blocker1 = self._make_perm("GuardDog1", "p2", [])
        blocker2 = self._make_perm("GuardDog2", "p2", [])
        blocker3 = self._make_perm("GuardDog3", "p2", [])
        gs.battlefield.extend([attacker, blocker1, blocker2, blocker3])

        assert can_block_menacing(gs, attacker.id, [blocker1.id, blocker2.id, blocker3.id]) is True

    def test_can_block_menace_one_blocker_illegal(self):
        """Menacing attacker CANNOT be blocked by only 1 creature."""
        gs = self._make_game()
        attacker = self._make_perm("BigCreature", "p1", ["menace"])
        blocker1 = self._make_perm("GuardDog", "p2", [])
        gs.battlefield.extend([attacker, blocker1])

        assert can_block_menacing(gs, attacker.id, [blocker1.id]) is False

    def test_can_block_menace_zero_blockers_illegal(self):
        """Menacing attacker CANNOT be blocked by 0 creatures (in a block declaration)."""
        gs = self._make_game()
        attacker = self._make_perm("BigCreature", "p1", ["menace"])
        gs.battlefield.append(attacker)

        assert can_block_menacing(gs, attacker.id, []) is False

    def test_can_block_attacker_not_on_battlefield(self):
        """can_block_menacing returns True if attacker not found (no menace assumed)."""
        gs = self._make_game()

        # Attacker doesn't exist on battlefield — treated as no menace
        assert can_block_menacing(gs, "nonexistent", ["blocker1"]) is True

    def test_can_block_menace_vs_non_menace_distinction(self):
        """Menace and non-menace attackers behave differently for single blocker."""
        gs = self._make_game()
        menace_attacker = self._make_perm("BigCreature", "p1", ["menace"])
        normal_attacker = self._make_perm("Wolf", "p1", ["haste"])
        blocker = self._make_perm("GuardDog", "p2", [])
        gs.battlefield.extend([menace_attacker, normal_attacker, blocker])

        # Menacing attacker: 1 blocker is illegal
        assert can_block_menacing(gs, menace_attacker.id, [blocker.id]) is False
        # Normal attacker: 1 blocker is legal
        assert can_block_menacing(gs, normal_attacker.id, [blocker.id]) is True
