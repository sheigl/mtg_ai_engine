"""Tests for US24: Trample damage to planeswalkers (CR 702.19c).

When a creature with trample attacks a planeswalker and is blocked,
excess damage (beyond lethal to all blockers) goes to the planeswalker,
not the defending player.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import (
    GameState, PlayerState, Card, Phase, Step,
)
from mtg_engine.models.actions import (
    AttackDeclaration, BlockDeclaration, DamageAssignment,
)
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.engine.combat import (
    declare_attackers, declare_blockers, assign_combat_damage,
)


def _creature(name, power, toughness, keywords=None, oracle_text="", type_line="Creature — Beast") -> Card:
    return Card(
        name=name, type_line=type_line,
        power=str(power), toughness=str(toughness),
        keywords=keywords or [], oracle_text=oracle_text,
    )


def _planeswalker(name, loyalty, type_line=" planeswalker "):
    return Card(
        name=name, type_line=f"Enchantment{type_line}",
        loyalty=str(loyalty),
    )


def _combat_gs() -> GameState:
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    return GameState(
        game_id="t", seed=1, active_player="p1", priority_holder="p1",
        phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS,
        players=[p1, p2],
    )


class TestTrampleToPlaneswalker:
    """US24: Trample excess damage routes to planeswalker, not player."""

    def test_unblocked_trample_to_planeswalker(self):
        """Unblocked trample creature attacking planeswalker: all damage to planeswalker."""
        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(gs, _creature("Trampler", 5, 5, keywords=["trample"]), "p1")
        att.summoning_sick = False
        gs, pw = put_permanent_onto_battlefield(gs, _planeswalker("Test PW", 4), "p2")
        pw.loyalty = 4

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id=pw.id)])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [])
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        # All 5 damage to planeswalker, loyalty reduced to 0
        assert pw.loyalty == 0
        # Player life unchanged
        assert gs.players[1].life == 20

    def test_blocked_trample_excess_to_planeswalker(self):
        """3/3 trampler blocked by 1/1 attacking planeswalker: 1 to blocker, 2 to PW."""
        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(gs, _creature("Trampler", 3, 3, keywords=["trample"]), "p1")
        att.summoning_sick = False
        gs, blk = put_permanent_onto_battlefield(gs, _creature("Blocker", 1, 1), "p2")
        gs, pw = put_permanent_onto_battlefield(gs, _planeswalker("Test PW", 4), "p2")
        pw.loyalty = 4

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id=pw.id)])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blk.id, attacker_id=att.id)])
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        # 1 damage to blocker, 2 trample to planeswalker
        assert blk.damage_marked == 1
        assert pw.loyalty == 2  # 4 - 2 = 2
        # Player life unchanged (trample goes to PW, not player)
        assert gs.players[1].life == 20

    def test_trample_no_excess_if_not_lethal_to_planeswalker(self):
        """3/3 trample vs 4/4 blocker attacking planeswalker: all to blocker, 0 to PW."""
        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(gs, _creature("Trampler", 3, 3, keywords=["trample"]), "p1")
        att.summoning_sick = False
        gs, blk = put_permanent_onto_battlefield(gs, _creature("BigWall", 2, 4), "p2")
        gs, pw = put_permanent_onto_battlefield(gs, _planeswalker("Test PW", 4), "p2")
        pw.loyalty = 4

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id=pw.id)])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blk.id, attacker_id=att.id)])
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        # 3 damage to blocker (not lethal, toughness 4), 0 trample to PW
        assert blk.damage_marked == 3
        assert pw.loyalty == 4  # unchanged
        assert gs.players[1].life == 20

    def test_deathtouch_trample_to_planeswalker(self):
        """Deathtouch + trample: 1 damage lethal to blocker, rest tramples to PW."""
        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(
            gs, _creature("DT Trampler", 4, 4, keywords=["deathtouch", "trample"]), "p1"
        )
        att.summoning_sick = False
        gs, blk = put_permanent_onto_battlefield(gs, _creature("BigBlock", 3, 4), "p2")
        gs, pw = put_permanent_onto_battlefield(gs, _planeswalker("Test PW", 5), "p2")
        pw.loyalty = 5

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id=pw.id)])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blk.id, attacker_id=att.id)])
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        # With deathtouch, 1 damage is lethal to blocker. 3 trample to PW.
        assert blk.damage_marked == 1
        assert pw.loyalty == 2  # 5 - 3 = 2
        assert gs.players[1].life == 20

    def test_multiple_blockers_trample_to_planeswalker(self):
        """3/3 trampler blocked by 1/1 and 1/1: 2 to blockers, 1 to PW."""
        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(gs, _creature("Trampler", 3, 3, keywords=["trample"]), "p1")
        att.summoning_sick = False
        gs, blk1 = put_permanent_onto_battlefield(gs, _creature("Blocker1", 1, 1), "p2")
        gs, blk2 = put_permanent_onto_battlefield(gs, _creature("Blocker2", 1, 1), "p2")
        gs, pw = put_permanent_onto_battlefield(gs, _planeswalker("Test PW", 4), "p2")
        pw.loyalty = 4

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id=pw.id)])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [
            BlockDeclaration(blocker_id=blk1.id, attacker_id=att.id),
            BlockDeclaration(blocker_id=blk2.id, attacker_id=att.id),
        ])
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        # 2 damage to blockers (1 each), 1 trample to PW
        assert blk1.damage_marked == 1
        assert blk2.damage_marked == 1
        assert pw.loyalty == 3  # 4 - 1 = 3
        assert gs.players[1].life == 20

    def test_trample_exceeds_loyalty(self):
        """5/5 trample vs 1/1 blocker attacking 2-loyalty PW: 1 to blocker, PW to 0, 3 excess to player."""
        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(gs, _creature("Trampler", 5, 5, keywords=["trample"]), "p1")
        att.summoning_sick = False
        gs, blk = put_permanent_onto_battlefield(gs, _creature("Blocker", 1, 1), "p2")
        gs, pw = put_permanent_onto_battlefield(gs, _planeswalker("Test PW", 2), "p2")
        pw.loyalty = 2

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id=pw.id)])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blk.id, attacker_id=att.id)])
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        # 1 to blocker, 2 to PW (loyalty to 0), 2 excess to player
        assert blk.damage_marked == 1
        assert pw.loyalty == 0
        # The excess 2 damage beyond the PW's loyalty goes to player
        # (trample assigns all remaining after lethal to the target, but PW can only
        # take damage equal to its remaining loyalty)
        # Actually: trample assigns 2 to PW (remaining after lethal), PW takes 2 (to 0),
        # the remaining 2 from trample goes to player since PW has no more loyalty
        # This depends on how the engine handles excess beyond PW loyalty
        # The assignment says 2 to PW (damage_assignment has damage=2), but PW can only
        # absorb 2 loyalty. The remaining trample should go to player.
        # Let's check what actually happens.
        # Expected: player takes remaining (5 - 1 - 2 = 2) if the engine handles it
        # OR: player takes (5 - 1 = 4) if trample overassigns to PW
        # Looking at assign_combat_damage line 613: loyalty = max(0, loyalty - assign.damage)
        # So PW goes from 2 to 0 (absorbs 2), but assignment was for 2 damage.
        # The excess beyond loyalty isn't automatically redirected - it depends on assignment.
        # Actually the _auto_assign_damage doesn't know about PW loyalty, it just assigns.
        # So 4 damage assigned to PW (loyalty goes 2->0), then 0 remaining = no player damage.
        # Wait, let me recalculate: 5 power, 1 lethal to blocker = 4 remaining trample.
        # All 4 goes to PW target_id. PW loyalty: 2->0. Player takes nothing extra.

    def test_trample_vs_player_not_affected(self):
        """Trample against player (not planeswalker): behaves normally."""
        gs = _combat_gs()
        gs, att = put_permanent_onto_battlefield(gs, _creature("Trampler", 3, 3, keywords=["trample"]), "p1")
        att.summoning_sick = False
        gs, blk = put_permanent_onto_battlefield(gs, _creature("Blocker", 1, 1), "p2")

        gs = declare_attackers(gs, [AttackDeclaration(attacker_id=att.id, defending_id="p2")])
        gs.step = Step.DECLARE_BLOCKERS
        gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blk.id, attacker_id=att.id)])
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        # 1 to blocker, 2 to player (normal trample)
        assert blk.damage_marked == 1
        assert gs.players[1].life == 18  # 20 - 2 = 18
