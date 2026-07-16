import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import uuid
from mtg_engine.ability.loyalty import (
    LoyaltyAbilityTracker,
    get_loyalty_tracker,
    reset_loyalty_tracker,
    can_activate_loyalty,
    activate_loyalty_ability,
    set_initial_loyalty,
    get_current_loyalty,
    check_loyalty_death,
)
from mtg_engine.models.game import (
    GameState, PlayerState, Card, Permanent, ManaPool, Phase, Step,
)


def _make_game_state(
    phase: Phase = Phase.PRECOMBAT_MAIN,
    step: Step = Step.MAIN,
    active_player: str = "Player1",
) -> GameState:
    """Create a minimal game state for testing."""
    player = PlayerState(
        name="Player1",
        life=20,
        mana_pool=ManaPool(),
        hand=[],
        library=[Card(name=f"Card{i}", type_line="Basic Land — Plains") for i in range(20)],
        graveyard=[],
        exile=[],
    )
    opponent = PlayerState(
        name="Player2",
        life=20,
        mana_pool=ManaPool(),
        hand=[],
        library=[],
        graveyard=[],
        exile=[],
    )
    return GameState(
        game_id="test",
        seed=42,
        players=[player, opponent],
        battlefield=[],
        stack=[],
        pending_triggers=[],
        active_player=active_player,
        priority_holder=active_player,
        phase=phase,
        step=step,
        turn=1,
    )


def _make_planeswalker(
    controller: str = "Player1",
    loyalty: int = 5,
    name: str = "Jace, Wielder of Mysteries",
) -> Permanent:
    """Create a test planeswalker permanent."""
    card = Card(
        name=name,
        type_line="Legendary Planeswalker — Human Wizard",
        loyalty=str(loyalty),
        colors=["U"],
    )
    perm = Permanent(
        id=str(uuid.uuid4()),
        card=card,
        controller=controller,
        counters={"loyalty": loyalty},
    )
    return perm


def setup_function():
    """Reset loyalty tracker before each test."""
    reset_loyalty_tracker()


# =====================================================================
# LoyaltyAbilityTracker tests
# =====================================================================

def test_tracker_initially_empty():
    tracker = LoyaltyAbilityTracker()
    assert not tracker.has_activated_this_turn("perm1")


def test_tracker_marks_activated():
    tracker = LoyaltyAbilityTracker()
    tracker.mark_activated("perm1")
    assert tracker.has_activated_this_turn("perm1")


def test_tracker_resets_new_turn():
    tracker = LoyaltyAbilityTracker()
    tracker.mark_activated("perm1")
    tracker.new_turn(2)
    assert not tracker.has_activated_this_turn("perm1")


def test_tracker_no_reset_same_turn():
    tracker = LoyaltyAbilityTracker()
    tracker.new_turn(1)  # Set turn to 1
    tracker.mark_activated("perm1")
    tracker.new_turn(1)  # Same turn - should NOT clear
    assert tracker.has_activated_this_turn("perm1")


# =====================================================================
# can_activate_loyalty tests
# =====================================================================

def test_can_activate_main_phase():
    gs = _make_game_state()
    perm = _make_planeswalker()
    gs.battlefield.append(perm)
    assert can_activate_loyalty(gs, perm, "Player1", -1)


def test_cannot_activate_wrong_controller():
    gs = _make_game_state()
    perm = _make_planeswalker(controller="Player2")
    gs.battlefield.append(perm)
    assert not can_activate_loyalty(gs, perm, "Player1", -1)


def test_cannot_activate_combat_phase():
    gs = _make_game_state(Phase.COMBAT, Step.DECLARE_ATTACKERS)
    perm = _make_planeswalker()
    gs.battlefield.append(perm)
    assert not can_activate_loyalty(gs, perm, "Player1", -1)


def test_cannot_activate_opponent_turn():
    gs = _make_game_state(Phase.PRECOMBAT_MAIN, Step.MAIN, "Player2")
    perm = _make_planeswalker()
    gs.battlefield.append(perm)
    assert not can_activate_loyalty(gs, perm, "Player1", -1)


def test_cannot_activate_stack_not_empty():
    gs = _make_game_state()
    gs.stack.append(Card(name="TestSpell", type_line="Instant"))
    perm = _make_planeswalker()
    gs.battlefield.append(perm)
    assert not can_activate_loyalty(gs, perm, "Player1", -1)


def test_cannot_activate_already_activated():
    gs = _make_game_state()
    perm = _make_planeswalker()
    gs.battlefield.append(perm)
    tracker = get_loyalty_tracker()
    tracker.mark_activated(perm.id)
    assert not can_activate_loyalty(gs, perm, "Player1", -1)


def test_cannot_activate_insufficient_loyalty():
    gs = _make_game_state()
    perm = _make_planeswalker(loyalty=1)
    gs.battlefield.append(perm)
    assert not can_activate_loyalty(gs, perm, "Player1", -2)


def test_can_activate_positive_loyalty():
    gs = _make_game_state()
    perm = _make_planeswalker(loyalty=1)
    gs.battlefield.append(perm)
    assert can_activate_loyalty(gs, perm, "Player1", +1)


def test_can_activate_zero_loyalty():
    gs = _make_game_state()
    perm = _make_planeswalker(loyalty=1)
    gs.battlefield.append(perm)
    assert can_activate_loyalty(gs, perm, "Player1", 0)


# =====================================================================
# activate_loyalty_ability tests
# =====================================================================

def test_activate_negative_loyalty():
    gs = _make_game_state()
    perm = _make_planeswalker(loyalty=5)
    gs.battlefield.append(perm)
    gs = activate_loyalty_ability(gs, perm, "Player1", -2, "Draw a card.")
    assert get_current_loyalty(perm) == 3


def test_activate_positive_loyalty():
    gs = _make_game_state()
    perm = _make_planeswalker(loyalty=5)
    gs.battlefield.append(perm)
    gs = activate_loyalty_ability(gs, perm, "Player1", +1, "Until end of turn, target creature gets -1/-1.")
    assert get_current_loyalty(perm) == 6


def test_activate_zero_loyalty():
    gs = _make_game_state()
    perm = _make_planeswalker(loyalty=5)
    gs.battlefield.append(perm)
    gs = activate_loyalty_ability(gs, perm, "Player1", 0, "Target player reveals their hand.")
    assert get_current_loyalty(perm) == 5


def test_activate_draw_effect():
    gs = _make_game_state()
    perm = _make_planeswalker(loyalty=5)
    gs.battlefield.append(perm)
    initial_hand = len(gs.players[0].hand)
    initial_library = len(gs.players[0].library)
    gs = activate_loyalty_ability(gs, perm, "Player1", -2, "Draw 2 cards.")
    assert len(gs.players[0].hand) == initial_hand + 2
    assert len(gs.players[0].library) == initial_library - 2


def test_activate_gain_life_effect():
    gs = _make_game_state()
    perm = _make_planeswalker(loyalty=5)
    gs.battlefield.append(perm)
    gs = activate_loyalty_ability(gs, perm, "Player1", +1, "You gain 3 life.")
    assert gs.players[0].life == 23


def test_activate_deal_damage_effect():
    gs = _make_game_state()
    perm = _make_planeswalker(loyalty=5)
    gs.battlefield.append(perm)
    gs = activate_loyalty_ability(gs, perm, "Player1", -2, "Deal 2 damage to target player.")
    assert gs.players[1].life == 18


def test_cannot_activate_twice():
    gs = _make_game_state()
    perm = _make_planeswalker(loyalty=5)
    gs.battlefield.append(perm)
    gs = activate_loyalty_ability(gs, perm, "Player1", -1, "Draw a card.")
    assert not can_activate_loyalty(gs, perm, "Player1", -1)


def test_activate_raises_on_invalid():
    gs = _make_game_state(Phase.COMBAT, Step.DECLARE_ATTACKERS)
    perm = _make_planeswalker()
    gs.battlefield.append(perm)
    try:
        activate_loyalty_ability(gs, perm, "Player1", -1, "Draw a card.")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# =====================================================================
# set_initial_loyalty tests
# =====================================================================

def test_set_initial_loyalty():
    perm = _make_planeswalker(loyalty=0)
    card = Card(name="TestPW", type_line="Planeswalker", loyalty="7")
    set_initial_loyalty(perm, card)
    assert get_current_loyalty(perm) == 7


def test_set_initial_loyalty_no_loyalty():
    perm = _make_planeswalker(loyalty=0)
    card = Card(name="TestPW", type_line="Planeswalker", loyalty=None)
    set_initial_loyalty(perm, card)
    assert get_current_loyalty(perm) == 0


# =====================================================================
# check_loyalty_death tests
# =====================================================================

def test_loyalty_death_zero():
    gs = _make_game_state()
    perm = _make_planeswalker(loyalty=0)
    gs.battlefield.append(perm)
    gs = check_loyalty_death(gs, perm)
    assert len(gs.battlefield) == 0
    assert len(gs.players[0].graveyard) == 1


def test_loyalty_death_negative():
    gs = _make_game_state()
    perm = _make_planeswalker(loyalty=-1)
    gs.battlefield.append(perm)
    gs = check_loyalty_death(gs, perm)
    assert len(gs.battlefield) == 0


def test_no_loyalty_death_positive():
    gs = _make_game_state()
    perm = _make_planeswalker(loyalty=3)
    gs.battlefield.append(perm)
    gs = check_loyalty_death(gs, perm)
    assert len(gs.battlefield) == 1


# =====================================================================
# get_current_loyalty test
# =====================================================================

def test_get_current_loyalty():
    perm = _make_planeswalker(loyalty=5)
    assert get_current_loyalty(perm) == 5
