import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import GameState, PlayerState, Card
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.engine.replacement import GameEvent, process_event, apply_damage_event


def _make_game() -> GameState:
    p1 = PlayerState(name="p1")
    p2 = PlayerState(name="p2")
    return GameState(game_id="t", seed=1, active_player="p1", priority_holder="p1", players=[p1, p2])


def test_shield_counter_prevents_destruction():
    """Shield counter: removed instead of creature being destroyed."""
    gs = _make_game()
    card = Card(name="Knight", type_line="Creature — Human Knight", power="2", toughness="2")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    perm.counters["shield"] = 1

    event = GameEvent(event_type="destroy", target_id=perm.id)
    event, gs = process_event(event, gs)

    assert event.cancelled
    assert perm.counters.get("shield", 0) == 0
    # Permanent still on battlefield
    assert any(p.id == perm.id for p in gs.battlefield)


def test_no_replacement_no_shield():
    """Without shield, destroy event is not cancelled."""
    gs = _make_game()
    card = Card(name="Creature", type_line="Creature — Beast", power="2", toughness="2")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")

    event = GameEvent(event_type="destroy", target_id=perm.id)
    event, gs = process_event(event, gs)

    assert not event.cancelled


def test_damage_to_player_reduces_life():
    gs = _make_game()
    gs = apply_damage_event(gs, "Lightning Bolt", [], "p2", 3)
    assert gs.players[1].life == 17


def test_infect_damage_to_creature_as_counters():
    gs = _make_game()
    card = Card(name="Creature", type_line="Creature — Beast", power="2", toughness="2")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    gs = apply_damage_event(gs, "Infect Source", ["infect"], perm.id, 2)
    assert perm.counters.get("-1/-1", 0) == 2
    assert perm.damage_marked == 0  # no regular damage


# ─── US4: Damage prevention replacement effects ───────────────────────────────

def test_prevent_all_combat_damage_fog():
    """prevent_all_combat_damage flag blocks all combat damage."""
    from mtg_engine.models.game import Phase, Step
    from mtg_engine.models.actions import AttackDeclaration
    from mtg_engine.engine.zones import put_permanent_onto_battlefield
    from mtg_engine.engine.combat import declare_attackers, assign_combat_damage

    gs = _make_game()
    gs.phase = Phase.COMBAT
    gs.step = Step.DECLARE_ATTACKERS
    card = Card(name="Bear", type_line="Creature — Bear", power="2", toughness="2")
    gs, attacker = put_permanent_onto_battlefield(gs, card, "p1")
    attacker.summoning_sick = False
    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    gs.step = Step.COMBAT_DAMAGE
    gs.prevent_all_combat_damage = True
    pre_life = gs.players[1].life
    gs = assign_combat_damage(gs)
    assert gs.players[1].life == pre_life  # no damage dealt
    assert not gs.prevent_all_combat_damage  # flag cleared


def test_damage_prevention_effect_reduces_damage():
    """DamagePreventionEffect with remaining=3 reduces 5 damage to 2."""
    from mtg_engine.models.game import DamagePreventionEffect
    gs = _make_game()
    card = Card(name="Target", type_line="Creature — Beast", power="2", toughness="5")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p2")
    prev = DamagePreventionEffect(remaining=3, target_id=perm.id)
    gs.prevention_effects.append(prev)
    gs = apply_damage_event(gs, "Source", [], perm.id, 5)
    assert perm.damage_marked == 2  # 5 - 3 = 2


def test_damage_prevention_depletes_remaining():
    """DamagePreventionEffect remaining is decremented after use."""
    from mtg_engine.models.game import DamagePreventionEffect
    gs = _make_game()
    card = Card(name="Target", type_line="Creature — Beast", power="2", toughness="5")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p2")
    prev = DamagePreventionEffect(remaining=3, target_id=perm.id)
    gs.prevention_effects.append(prev)
    gs = apply_damage_event(gs, "Source", [], perm.id, 2)
    # 2 damage fully prevented; remaining should be 1
    assert perm.damage_marked == 0
    assert len(gs.prevention_effects) == 1
    assert gs.prevention_effects[0].remaining == 1


def test_protection_from_red_prevents_damage():
    """Protection from red prevents damage from a red source."""
    gs = _make_game()
    card = Card(
        name="Protected", type_line="Creature — Angel",
        power="2", toughness="2",
        keywords=["protection from red"],
    )
    gs, perm = put_permanent_onto_battlefield(gs, card, "p2")
    gs = apply_damage_event(gs, "Lightning Bolt", ["R"], perm.id, 3)
    assert perm.damage_marked == 0  # protection prevents all damage


def test_protection_does_not_prevent_non_matching_color():
    """Protection from red does NOT prevent blue damage."""
    gs = _make_game()
    card = Card(
        name="Protected", type_line="Creature — Angel",
        power="2", toughness="2",
        keywords=["protection from red"],
    )
    gs, perm = put_permanent_onto_battlefield(gs, card, "p2")
    gs = apply_damage_event(gs, "Counterspell Source", ["U"], perm.id, 3)
    assert perm.damage_marked == 3  # blue damage not prevented
