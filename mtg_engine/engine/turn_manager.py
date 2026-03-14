"""
Turn structure and priority management. REQ-T01, REQ-S01, REQ-S02.
CR 500-511: turn structure and phase/step rules.
"""
import logging

from mtg_engine.models.game import GameState, ManaPool, Phase, Step

logger = logging.getLogger(__name__)

# Ordered sequence of (Phase, Step) pairs for a full turn. REQ-T01
TURN_SEQUENCE: list[tuple[Phase, Step]] = [
    (Phase.BEGINNING, Step.UNTAP),
    (Phase.BEGINNING, Step.UPKEEP),
    (Phase.BEGINNING, Step.DRAW),
    (Phase.PRECOMBAT_MAIN, Step.MAIN),
    (Phase.COMBAT, Step.BEGINNING_OF_COMBAT),
    (Phase.COMBAT, Step.DECLARE_ATTACKERS),
    (Phase.COMBAT, Step.DECLARE_BLOCKERS),
    (Phase.COMBAT, Step.FIRST_STRIKE_DAMAGE),
    (Phase.COMBAT, Step.COMBAT_DAMAGE),
    (Phase.COMBAT, Step.END_OF_COMBAT),
    (Phase.POSTCOMBAT_MAIN, Step.MAIN),
    (Phase.ENDING, Step.END),
    (Phase.ENDING, Step.CLEANUP),
]


def _other_player(game_state: GameState) -> str:
    """Return the name of the non-active player."""
    for p in game_state.players:
        if p.name != game_state.active_player:
            return p.name
    raise ValueError("Could not find non-active player")


def begin_step(game_state: GameState) -> GameState:
    """
    Apply start-of-step effects for the current phase/step.
    REQ-T03: Untap, REQ-T04: Draw, REQ-T05: Cleanup.
    """
    from mtg_engine.engine.zones import get_player, draw_card

    step = game_state.step

    if step == Step.UNTAP:
        # REQ-T03: untap active player's permanents; no priority granted in untap step
        for perm in game_state.battlefield:
            if perm.controller == game_state.active_player:
                perm.tapped = False
                perm.summoning_sick = False  # remove summoning sickness at start of turn
        # Reset lands played this turn
        active = get_player(game_state, game_state.active_player)
        active.lands_played_this_turn = 0
        # No priority in untap step; mana pools don't need clearing
        return game_state

    elif step == Step.DRAW:
        # REQ-T04: active player draws one card (first-player first-turn exception
        # is handled at game creation, not here)
        game_state, _ = draw_card(game_state, game_state.active_player)

    elif step == Step.CLEANUP:
        # REQ-T05: discard to max hand size, remove damage, end "until end of turn" effects
        active = get_player(game_state, game_state.active_player)
        while len(active.hand) > active.max_hand_size:
            active.hand.pop()  # simplified: discard last card (full impl requires player choice)
        for perm in game_state.battlefield:
            perm.damage_marked = 0
        # Clear mana pools at cleanup
        for p in game_state.players:
            p.mana_pool = ManaPool()
        return game_state

    # Clear mana pools at end of each step (mana floating rule)
    # Untap and Cleanup already handled above
    if step not in (Step.UNTAP, Step.CLEANUP):
        for p in game_state.players:
            p.mana_pool = ManaPool()

    return game_state


def advance_step(game_state: GameState) -> GameState:
    """
    Move to the next step/phase in the turn sequence.
    Applies start-of-step effects and grants priority. REQ-T01, REQ-S01.
    """
    current = (game_state.phase, game_state.step)
    try:
        idx = TURN_SEQUENCE.index(current)
    except ValueError:
        logger.warning("Current (phase, step) not in TURN_SEQUENCE: %s; resetting to index 0", current)
        idx = -1

    if idx + 1 < len(TURN_SEQUENCE):
        next_phase, next_step = TURN_SEQUENCE[idx + 1]
        game_state.phase = next_phase
        game_state.step = next_step
    else:
        # End of turn — advance to next player's turn
        game_state = _advance_turn(game_state)

    game_state = begin_step(game_state)

    # Grant priority to active player (except untap step — no priority there). REQ-S01
    if game_state.step != Step.UNTAP:
        game_state.priority_holder = game_state.active_player

    return game_state


def _advance_turn(game_state: GameState) -> GameState:
    """Switch to the next player's turn."""
    other = _other_player(game_state)
    game_state.active_player = other
    game_state.priority_holder = other
    game_state.turn += 1
    game_state.phase = Phase.BEGINNING
    game_state.step = Step.UNTAP
    logger.info("Turn %d begins; active player: %s", game_state.turn, game_state.active_player)
    return game_state


def pass_priority(game_state: GameState, player_name: str) -> GameState:
    """
    Handle priority passing. REQ-S01, REQ-S02.

    If both players pass consecutively:
    - If stack is non-empty: resolve top of stack
    - If stack is empty: advance step
    """
    if game_state.priority_holder != player_name:
        raise ValueError(f"{player_name} does not have priority (holder: {game_state.priority_holder!r})")

    other = _other_player(game_state)

    if game_state.stack:
        # Stack is non-empty. REQ-S02: both players must pass for resolution.
        if game_state.priority_holder == game_state.active_player:
            # Active player passed with stack — give priority to other player
            game_state.priority_holder = other
        else:
            # Non-active player passed with stack non-empty AND active player already passed
            # → both have passed in succession: resolve top of stack
            from mtg_engine.engine.stack import resolve_top
            game_state = resolve_top(game_state)
            game_state.priority_holder = game_state.active_player
    else:
        # Stack is empty
        if game_state.priority_holder == game_state.active_player:
            # Active player passes on empty stack → give priority to other
            game_state.priority_holder = other
        else:
            # Both passed on empty stack → advance step. REQ-S02
            game_state = advance_step(game_state)

    return game_state
