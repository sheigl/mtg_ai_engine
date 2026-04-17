"""Tests for US25: Flanking (CR 702.25a).

Flanking: Whenever this creature becomes blocked by a creature without flanking,
the blocking creature gets -1/-1 until end of turn.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import (
    GameState, PlayerState, Card, Phase, Step,
)
from mtg_engine.models.actions import (
    AttackDeclaration, BlockDeclaration,
)
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.engine.combat import (
    declare_attackers, declare_blockers,
)


def _creature(name, power, toughness, keywords=None, oracle_text="", type_line="Creature — Beast") -> Card:
    return Card(
        name=name, type_line=type_line,
        power=str(power), toughness=str(toughness),
        keywords=keywords or [], oracle_text=oracle_text,
    )


def _combat_gs() -> GameState:
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    return GameState(
        game_id="t", seed=1, active_player="p1", priority_holder="p1",
        phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS,
        players=[p1, p2],
    )


class TestFlanking:
    """US25: Flanking gives -1/-1 to blocking creatures without flanking."""

    def test_flanking_applies_minus_one_minus_one(self):
        """Attacker with flanking blocked by creature without flanking: -1/-1."""
        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(gs, _creature("Elf Warrior", 2, 2, keywords=["flanking"]), "p1")
        att.summoning_sick = False
        gs, blk = put_permanent_onto_battlefield(gs, _creature("Goblin", 1, 1), "p2")

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id="p2")])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blk.id, attacker_id=att.id)])

        # Blocker gets -1/-1 until end of turn
        assert blk.power_bonus == -1
        assert blk.toughness_bonus == -1
        assert blk.power_bonus_expires == "end_of_turn"
        assert blk.toughness_bonus_expires == "end_of_turn"

    def test_flanking_no_effect_if_both_have_flanking(self):
        """If blocker also has flanking, no -1/-1 is applied."""
        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(gs, _creature("Elf Warrior", 2, 2, keywords=["flanking"]), "p1")
        att.summoning_sick = False
        gs, blk = put_permanent_onto_battlefield(gs, _creature("Elf Defender", 1, 1, keywords=["flanking"]), "p2")

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id="p2")])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blk.id, attacker_id=att.id)])

        # No bonus applied since both have flanking
        assert blk.power_bonus == 0
        assert blk.toughness_bonus == 0

    def test_flanking_no_effect_if_attacker_lacks_flanking(self):
        """If attacker lacks flanking, no -1/-1 is applied regardless of blocker."""
        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(gs, _creature("Goblin Raider", 2, 1, keywords=[]), "p1")
        att.summoning_sick = False
        gs, blk = put_permanent_onto_battlefield(gs, _creature("Oaf", 1, 2), "p2")

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id="p2")])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blk.id, attacker_id=att.id)])

        assert blk.power_bonus == 0
        assert blk.toughness_bonus == 0

    def test_multiple_blockers_flanking(self):
        """Multiple blockers: each blocked creature without flanking gets -1/-1."""
        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(gs, _creature("Elf Warrior", 2, 2, keywords=["flanking"]), "p1")
        att.summoning_sick = False
        gs, blk1 = put_permanent_onto_battlefield(gs, _creature("Goblin", 1, 1), "p2")
        gs, blk2 = put_permanent_onto_battlefield(gs, _creature("Oaf", 1, 2), "p2")
        gs, blk3 = put_permanent_onto_battlefield(gs, _creature("Elf Guard", 1, 1, keywords=["flanking"]), "p2")

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id="p2")])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [
            BlockDeclaration(blocker_id=blk1.id, attacker_id=att.id),
            BlockDeclaration(blocker_id=blk2.id, attacker_id=att.id),
            BlockDeclaration(blocker_id=blk3.id, attacker_id=att.id),
        ])

        # blk1 and blk2 get -1/-1 (no flanking), blk3 does not (has flanking)
        assert blk1.power_bonus == -1
        assert blk1.toughness_bonus == -1
        assert blk2.power_bonus == -1
        assert blk2.toughness_bonus == -1
        assert blk3.power_bonus == 0
        assert blk3.toughness_bonus == 0

    def test_flanking_affects_effective_power_toughness(self):
        """Flanking -1/-1 should reduce effective power and toughness."""
        from mtg_engine.engine.combat import _effective_power, _effective_toughness

        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(gs, _creature("Elf Warrior", 2, 2, keywords=["flanking"]), "p1")
        att.summoning_sick = False
        gs, blk = put_permanent_onto_battlefield(gs, _creature("Goblin", 3, 3), "p2")

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id="p2")])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blk.id, attacker_id=att.id)])

        # Effective P/T should reflect -1/-1
        assert _effective_power(blk) == 2  # 3 + (-1) = 2
        assert _effective_toughness(blk) == 2  # 3 + (-1) = 2

    def test_flanking_unblocked_no_effect(self):
        """Unblocked attacker: flanking has no effect (no blocker to penalize)."""
        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(gs, _creature("Elf Warrior", 3, 3, keywords=["flanking"]), "p1")
        att.summoning_sick = False

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id="p2")])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [])

        assert len(gs.combat.attackers) == 1
        assert gs.combat.attackers[0].is_blocked is False

    def test_flanking_with_other_keywords(self):
        """Flanking works alongside other keywords on blocker."""
        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(gs, _creature("Elf Warrior", 2, 2, keywords=["flanking"]), "p1")
        att.summoning_sick = False
        gs, blk = put_permanent_onto_battlefield(gs, _creature("Flying Brute", 2, 2, keywords=["flying"]), "p2")

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id="p2")])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blk.id, attacker_id=att.id)])

        assert blk.power_bonus == -1
        assert blk.toughness_bonus == -1

    def test_flanking_stacked_by_multiple_attackers(self):
        """Two different attackers with flanking blocking same creature: stacked -1/-1."""
        gs = _combat_gs()
        gs, att1 = put_permanent_onto_battlefield(gs, _creature("Elf Warrior", 2, 2, keywords=["flanking"]), "p1")
        att1.summoning_sick = False
        gs, att2 = put_permanent_onto_battlefield(gs, _creature("Elf Archer", 1, 1, keywords=["flanking", "flying"]), "p1")
        att2.summoning_sick = False
        gs, blk = put_permanent_onto_battlefield(gs, _creature("Goblin", 2, 2, keywords=["reach"]), "p2")

        gs = declare_attackers(gs, [
            AttackDeclaration(attacker_id=att1.id, defending_id="p2"),
            AttackDeclaration(attacker_id=att2.id, defending_id="p2"),
        ])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [
            BlockDeclaration(blocker_id=blk.id, attacker_id=att1.id),
            BlockDeclaration(blocker_id=blk.id, attacker_id=att2.id),
        ])

        # -1/-1 from each flanking attacker: -2/-2 total
        assert blk.power_bonus == -2
        assert blk.toughness_bonus == -2
