import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.ability.timing import (
    TimingRestriction,
    can_activate,
    parse_timing_restriction,
    get_current_timing,
)
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool, Phase, Step


def _make_game_state(
    phase: Phase = Phase.PRECOMBAT_MAIN,
    step: Step = Step.MAIN,
    active_player: str = "Player1",
) -> GameState:
    """Create a minimal game state with specified phase/step."""
    player = PlayerState(
        name="Player1",
        life=20,
        mana_pool=ManaPool(),
        hand=[],
        library=[],
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


# =====================================================================
# can_activate tests
# =====================================================================

def test_any_time_always_allowed():
    gs = _make_game_state()
    assert can_activate(gs, TimingRestriction.ANY_TIME, "Player1")


def test_instant_speed_always_allowed():
    gs = _make_game_state()
    assert can_activate(gs, TimingRestriction.INSTANT_SPEED, "Player1")


def test_sorcery_speed_main_phase():
    gs = _make_game_state(Phase.PRECOMBAT_MAIN, Step.MAIN)
    assert can_activate(gs, TimingRestriction.SORCERY_SPEED, "Player1")


def test_sorcery_speed_not_opponent_turn():
    gs = _make_game_state(Phase.PRECOMBAT_MAIN, Step.MAIN, "Player2")
    assert not can_activate(gs, TimingRestriction.SORCERY_SPEED, "Player1")


def test_sorcery_speed_not_combat():
    gs = _make_game_state(Phase.COMBAT, Step.DECLARE_ATTACKERS)
    assert not can_activate(gs, TimingRestriction.SORCERY_SPEED, "Player1")


def test_sorcery_speed_stack_not_empty():
    gs = _make_game_state(Phase.PRECOMBAT_MAIN, Step.MAIN)
    gs.stack.append(Card(name="TestSpell", type_line="Instant"))
    assert not can_activate(gs, TimingRestriction.SORCERY_SPEED, "Player1")


def test_your_main_phase():
    gs = _make_game_state(Phase.PRECOMBAT_MAIN, Step.MAIN)
    assert can_activate(gs, TimingRestriction.YOUR_MAIN_PHASE, "Player1")


def test_your_main_phase_not_combat():
    gs = _make_game_state(Phase.COMBAT, Step.DECLARE_ATTACKERS)
    assert not can_activate(gs, TimingRestriction.YOUR_MAIN_PHASE, "Player1")


def test_your_main_phase_not_opponent():
    gs = _make_game_state(Phase.PRECOMBAT_MAIN, Step.MAIN, "Player2")
    assert not can_activate(gs, TimingRestriction.YOUR_MAIN_PHASE, "Player1")


def test_opponent_turn():
    gs = _make_game_state(Phase.PRECOMBAT_MAIN, Step.MAIN, "Player2")
    assert can_activate(gs, TimingRestriction.OPPONENT_TURN, "Player1")


def test_opponent_turn_not_your_turn():
    gs = _make_game_state(Phase.PRECOMBAT_MAIN, Step.MAIN, "Player1")
    assert not can_activate(gs, TimingRestriction.OPPONENT_TURN, "Player1")


def test_your_turn():
    gs = _make_game_state(Phase.PRECOMBAT_MAIN, Step.MAIN, "Player1")
    assert can_activate(gs, TimingRestriction.YOUR_TURN, "Player1")


def test_your_turn_not_opponent():
    gs = _make_game_state(Phase.PRECOMBAT_MAIN, Step.MAIN, "Player2")
    assert not can_activate(gs, TimingRestriction.YOUR_TURN, "Player1")


def test_combat_phase():
    gs = _make_game_state(Phase.COMBAT, Step.DECLARE_ATTACKERS)
    assert can_activate(gs, TimingRestriction.COMBAT_PHASE, "Player1")


def test_combat_phase_not_main():
    gs = _make_game_state(Phase.PRECOMBAT_MAIN, Step.MAIN)
    assert not can_activate(gs, TimingRestriction.COMBAT_PHASE, "Player1")


def test_declare_attackers():
    gs = _make_game_state(Phase.COMBAT, Step.DECLARE_ATTACKERS)
    assert can_activate(gs, TimingRestriction.DECLARE_ATTACKERS, "Player1")


def test_declare_attackers_not_main():
    gs = _make_game_state(Phase.PRECOMBAT_MAIN, Step.MAIN)
    assert not can_activate(gs, TimingRestriction.DECLARE_ATTACKERS, "Player1")


def test_declare_blockers():
    gs = _make_game_state(Phase.COMBAT, Step.DECLARE_BLOCKERS)
    assert can_activate(gs, TimingRestriction.DECLARE_BLOCKERS, "Player1")


def test_damage_step():
    gs = _make_game_state(Phase.COMBAT, Step.COMBAT_DAMAGE)
    assert can_activate(gs, TimingRestriction.DAMAGE_STEP, "Player1")


def test_first_strike_damage():
    gs = _make_game_state(Phase.COMBAT, Step.FIRST_STRIKE_DAMAGE)
    assert can_activate(gs, TimingRestriction.DAMAGE_STEP, "Player1")


def test_beginning_of_combat():
    gs = _make_game_state(Phase.COMBAT, Step.BEGINNING_OF_COMBAT)
    assert can_activate(gs, TimingRestriction.BEGINNING_OF_COMBAT, "Player1")


def test_end_of_combat():
    gs = _make_game_state(Phase.COMBAT, Step.END_OF_COMBAT)
    assert can_activate(gs, TimingRestriction.END_OF_COMBAT, "Player1")


def test_upkeep():
    gs = _make_game_state(Phase.BEGINNING, Step.UPKEEP)
    assert can_activate(gs, TimingRestriction.UPKEEP, "Player1")


def test_end_step():
    gs = _make_game_state(Phase.ENDING, Step.END)
    assert can_activate(gs, TimingRestriction.END_STEP, "Player1")


def test_cleanup():
    gs = _make_game_state(Phase.ENDING, Step.CLEANUP)
    assert can_activate(gs, TimingRestriction.CLEANUP, "Player1")


def test_loyalty_ability_main_phase():
    gs = _make_game_state(Phase.PRECOMBAT_MAIN, Step.MAIN)
    assert can_activate(gs, TimingRestriction.LOYALTY_ABILITY, "Player1")


def test_loyalty_ability_not_combat():
    gs = _make_game_state(Phase.COMBAT, Step.DECLARE_ATTACKERS)
    assert not can_activate(gs, TimingRestriction.LOYALTY_ABILITY, "Player1")


# =====================================================================
# parse_timing_restriction tests
# =====================================================================

def test_parse_sorcery():
    assert parse_timing_restriction("(Activate only as a sorcery.)") == TimingRestriction.SORCERY_SPEED


def test_parse_your_turn():
    assert parse_timing_restriction("(Activate only during your turn.)") == TimingRestriction.YOUR_TURN


def test_parse_opponent_turn():
    assert parse_timing_restriction("(Activate only during an opponent's turn.)") == TimingRestriction.OPPONENT_TURN


def test_parse_combat():
    assert parse_timing_restriction("(Activate only during combat.)") == TimingRestriction.COMBAT_PHASE


def test_parse_main_phase():
    assert parse_timing_restriction("(Activate only during your main phase.)") == TimingRestriction.YOUR_MAIN_PHASE


def test_parse_declare_attackers():
    assert parse_timing_restriction("Declare attackers only.") == TimingRestriction.DECLARE_ATTACKERS


def test_parse_declare_blockers():
    assert parse_timing_restriction("Declare blockers only.") == TimingRestriction.DECLARE_BLOCKERS


def test_parse_damage():
    assert parse_timing_restriction("Damage step only.") == TimingRestriction.DAMAGE_STEP


def test_parse_beginning_combat():
    assert parse_timing_restriction("Beginning of combat only.") == TimingRestriction.BEGINNING_OF_COMBAT


def test_parse_end_combat():
    assert parse_timing_restriction("End of combat only.") == TimingRestriction.END_OF_COMBAT


def test_parse_upkeep():
    assert parse_timing_restriction("Upkeep only.") == TimingRestriction.UPKEEP


def test_parse_end_step():
    assert parse_timing_restriction("End step only.") == TimingRestriction.END_STEP


def test_parse_unknown():
    assert parse_timing_restriction("Some unknown text") == TimingRestriction.ANY_TIME


# =====================================================================
# get_current_timing test
# =====================================================================

def test_get_current_timing():
    gs = _make_game_state(Phase.COMBAT, Step.DECLARE_ATTACKERS)
    assert "combat" in get_current_timing(gs)
    assert "declare_attackers" in get_current_timing(gs)
