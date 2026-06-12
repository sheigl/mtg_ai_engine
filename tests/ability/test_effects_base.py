"""Tests for effect base classes."""
import sys
import os
# Add project root to path - go up from tests/ability/test_*.py to project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card, ManaPool
from mtg_engine.ability.effects.base import (
    DamageEffect, DestroyEffect, DrawEffect,
    ExileEffect, GainLifeEffect,
)


def _make_test_game() -> GameState:
    """Create a basic test game."""
    bolt = Card(
        name="Lightning Bolt",
        type_line="Instant",
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        mana_cost="{R}",
    )
    bear = Card(
        name="Grizzly Bears",
        type_line="Creature — Bear",
        oracle_text="",
        power="2",
        toughness="2",
    )
    forest = Card(
        name="Forest",
        type_line="Basic Land — Forest",
        oracle_text="{T}: Add {G}.",
    )
    p1 = PlayerState(
        name="p1", life=20, hand=[bolt], mana_pool=ManaPool(R=1),
        library=[forest for _ in range(5)]
    )
    p2 = PlayerState(
        name="p2", life=20, hand=[bear],
        library=[forest for _ in range(5)]
    )
    return GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
    )


def test_damage_effect_deals_damage_to_player():
    """DamageEffect deals damage to player."""
    gs = _make_test_game()
    effect = DamageEffect()
    
    assert gs.players[1].life == 20
    
    gs = effect.resolve(gs, gs.players[0].hand[0], targets=["p2"], controller_name="p1")
    
    assert gs.players[1].life == 17


def test_damage_effect_deals_damage_to_creature():
    """DamageEffect deals damage to creature."""
    from mtg_engine.engine.zones import put_permanent_onto_battlefield
    
    gs = _make_test_game()
    
    gs, bear_perm = put_permanent_onto_battlefield(
        gs, gs.players[1].hand[0], "p2"
    )
    
    effect = DamageEffect()
    
    assert bear_perm.damage_marked == 0
    
    gs = effect.resolve(gs, gs.players[0].hand[0], targets=[bear_perm.id], controller_name="p1")


def test_destroy_effect_checks_indestructible():
    """DestroyEffect checks indestructible."""
    from mtg_engine.engine.zones import put_permanent_onto_battlefield
    
    gs = _make_test_game()
    
    indestructible_card = Card(
        name="Darksteel Colossus",
        type_line="Artifact Creature — Beast",
        oracle_text="Indestructible",
        power="11",
        toughness="11",
        keywords=["indestructible"],
    )
    
    gs, perm = put_permanent_onto_battlefield(gs, indestructible_card, "p2")
    
    effect = DestroyEffect()
    
    initial_battlefield_count = len(gs.battlefield)
    
    gs = effect.resolve(gs, gs.players[0].hand[0], targets=[perm.id], controller_name="p2")
    
    assert len(gs.battlefield) == initial_battlefield_count


def test_destroy_effect_destroys_normal_creature():
    """DestroyEffect destroys normal creature."""
    from mtg_engine.engine.zones import put_permanent_onto_battlefield
    
    gs = _make_test_game()
    
    gs, perm = put_permanent_onto_battlefield(
        gs, gs.players[1].hand[0], "p2"
    )
    
    effect = DestroyEffect()
    
    gs = effect.resolve(gs, gs.players[0].hand[0], targets=[perm.id], controller_name="p1")
    
    assert len(gs.battlefield) == 0
    # Goes to controller's graveyard (p1), not opponent's
    assert len(gs.players[0].graveyard) == 1
    assert gs.players[0].graveyard[0].name == "Grizzly Bears"


def test_draw_effect_draws_cards():
    """DrawEffect draws cards."""
    gs = _make_test_game()
    effect = DrawEffect()
    
    initial_hand_size = len(gs.players[0].hand)
    
    gs = effect.resolve(gs, gs.players[0].hand[0], targets=None, controller_name="p1")
    
    assert len(gs.players[0].hand) == initial_hand_size + 1


def test_exile_effect_exiles_permanent():
    """ExileEffect exiles permanent."""
    from mtg_engine.engine.zones import put_permanent_onto_battlefield
    
    gs = _make_test_game()
    
    gs, perm = put_permanent_onto_battlefield(
        gs, gs.players[1].hand[0], "p2"
    )
    
    effect = ExileEffect()
    
    gs = effect.resolve(gs, gs.players[0].hand[0], targets=[perm.id], controller_name="p1")
    
    assert len(gs.battlefield) == 0
    # Check exile via player's exile zone
    assert len(gs.players[0].exile) == 1


def test_gain_life_effect_gains_life():
    """GainLifeEffect gains life."""
    gs = _make_test_game()
    effect = GainLifeEffect()
    
    assert gs.players[0].life == 20
    
    gs = effect.resolve(gs, gs.players[0].hand[0], targets=None, controller_name="p1")
    
    assert gs.players[0].life == 21


def test_effect_registry_get_effect():
    """Effect registry can get effect classes."""
    from mtg_engine.ability.effects.base import get_effect, create_effect
    
    effect_class = get_effect("damage")
    assert effect_class == DamageEffect
    
    effect_instance = create_effect("damage")
    assert isinstance(effect_instance, DamageEffect)


def test_effect_registry_create_effect():
    """Effect registry can create effect instances."""
    from mtg_engine.ability.effects.base import create_effect
    
    damage = create_effect("damage")
    assert damage is not None
    
    destroy = create_effect("destroy")
    assert destroy is not None
    
    nonexistent = create_effect("nonexistent")
    assert nonexistent is None