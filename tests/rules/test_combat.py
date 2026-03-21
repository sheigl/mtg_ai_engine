import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import GameState, PlayerState, Card, Phase, Step, ManaPool
from mtg_engine.models.actions import AttackDeclaration, BlockDeclaration, DamageAssignment
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.engine.combat import (
    declare_attackers, declare_blockers, assign_combat_damage, end_combat
)
from mtg_engine.engine.sba import check_and_apply_sbas


def _make_combat_game() -> GameState:
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    return GameState(
        game_id="t", seed=1, active_player="p1", priority_holder="p1",
        phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS,
        players=[p1, p2]
    )


def _add_creature(gs, name, power, toughness, controller, keywords=None):
    card = Card(
        name=name,
        type_line="Creature — Beast",
        power=str(power),
        toughness=str(toughness),
        keywords=keywords or [],
    )
    return put_permanent_onto_battlefield(gs, card, controller)


def test_declare_attacker_taps_creature():
    gs = _make_combat_game()
    gs, attacker = _add_creature(gs, "Bear", 2, 2, "p1")
    attacker.summoning_sick = False

    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    assert attacker.tapped


def test_vigilance_does_not_tap():
    gs = _make_combat_game()
    gs, attacker = _add_creature(gs, "Angel", 3, 3, "p1", keywords=["vigilance"])
    attacker.summoning_sick = False

    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    assert not attacker.tapped


def test_summoning_sick_cannot_attack():
    gs = _make_combat_game()
    gs, attacker = _add_creature(gs, "Bear", 2, 2, "p1")
    attacker.summoning_sick = True

    try:
        declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
        assert False, "Should raise"
    except ValueError:
        pass


def test_haste_ignores_summoning_sick():
    gs = _make_combat_game()
    gs, attacker = _add_creature(gs, "Rager", 3, 1, "p1", keywords=["haste"])
    attacker.summoning_sick = True

    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    assert len(gs.combat.attackers) == 1


def test_unblocked_attacker_deals_damage_to_player():
    gs = _make_combat_game()
    gs, attacker = _add_creature(gs, "Bear", 2, 2, "p1")
    attacker.summoning_sick = False

    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    gs.step = Step.COMBAT_DAMAGE
    gs = assign_combat_damage(gs)
    assert gs.players[1].life == 18


def test_blocked_attacker_deals_damage_to_blocker():
    gs = _make_combat_game()
    gs, attacker = _add_creature(gs, "Attacker", 3, 3, "p1")
    attacker.summoning_sick = False
    gs, blocker = _add_creature(gs, "Blocker", 1, 1, "p2")

    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    gs.step = Step.DECLARE_BLOCKERS
    gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blocker.id, attacker_id=attacker.id)])
    gs.step = Step.COMBAT_DAMAGE
    gs = assign_combat_damage(gs)

    # Blocker should be dead (3 damage ≥ 1 toughness)
    gs, events = check_and_apply_sbas(gs)
    assert not any(p.id == blocker.id for p in gs.battlefield)
    # Player takes no trample damage (no trample)
    assert gs.players[1].life == 20


def test_trample_excess_to_player():
    """3/3 trampler blocked by 1/1: 1 to blocker, 2 to player. REQ-R09"""
    gs = _make_combat_game()
    gs, attacker = _add_creature(gs, "Trampler", 3, 3, "p1", keywords=["trample"])
    attacker.summoning_sick = False
    gs, blocker = _add_creature(gs, "Blocker", 1, 1, "p2")

    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    gs.step = Step.DECLARE_BLOCKERS
    gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blocker.id, attacker_id=attacker.id)])
    gs.step = Step.COMBAT_DAMAGE
    gs = assign_combat_damage(gs)

    # Player should take 2 trample damage
    assert gs.players[1].life == 18, f"Expected 18, got {gs.players[1].life}"


def test_deathtouch_kills_larger_creature():
    """Deathtouch 1/1 blocks 5/5: both die. REQ-R10"""
    gs = _make_combat_game()
    gs, big = _add_creature(gs, "Titan", 5, 5, "p1")
    big.summoning_sick = False
    gs, deathtoucher = _add_creature(gs, "Deathtouch", 1, 1, "p2", keywords=["deathtouch"])

    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=big.id, defending_id="p2")])
    gs.step = Step.DECLARE_BLOCKERS
    gs = declare_blockers(gs, [BlockDeclaration(blocker_id=deathtoucher.id, attacker_id=big.id)])
    gs.step = Step.COMBAT_DAMAGE
    gs = assign_combat_damage(gs)
    gs, events = check_and_apply_sbas(gs)

    # Both die
    assert len(gs.battlefield) == 0, f"Expected 0 permanents, got {len(gs.battlefield)}"


def test_lifelink_gains_life():
    """Lifelink attacker deals 3 damage: controller gains 3 life. REQ-R11"""
    gs = _make_combat_game()
    gs, attacker = _add_creature(gs, "Lifelinker", 3, 3, "p1", keywords=["lifelink"])
    attacker.summoning_sick = False

    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    gs.step = Step.COMBAT_DAMAGE
    gs = assign_combat_damage(gs)

    assert gs.players[0].life == 23  # 20 + 3 lifelink
    assert gs.players[1].life == 17  # 20 - 3


def test_flying_creature_cannot_be_blocked_by_non_flyer():
    gs = _make_combat_game()
    gs, attacker = _add_creature(gs, "Flyer", 2, 2, "p1", keywords=["flying"])
    attacker.summoning_sick = False
    gs, blocker = _add_creature(gs, "Ground", 2, 2, "p2")  # no flying or reach

    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    gs.step = Step.DECLARE_BLOCKERS
    try:
        gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blocker.id, attacker_id=attacker.id)])
        assert False, "Should raise: ground creature cannot block flyer"
    except ValueError:
        pass


def test_reach_can_block_flyer():
    gs = _make_combat_game()
    gs, attacker = _add_creature(gs, "Flyer", 2, 2, "p1", keywords=["flying"])
    attacker.summoning_sick = False
    gs, blocker = _add_creature(gs, "Reach", 2, 2, "p2", keywords=["reach"])

    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    gs.step = Step.DECLARE_BLOCKERS
    gs = declare_blockers(gs, [BlockDeclaration(blocker_id=blocker.id, attacker_id=attacker.id)])
    assert len(gs.combat.attackers[0].blocker_ids) == 1
