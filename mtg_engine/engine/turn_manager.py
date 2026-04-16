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
                # US17 (T041): Reset loyalty_activated_this_turn flag at start of turn
                perm.loyalty_activated_this_turn = False
        # Reset lands played this turn
        active = get_player(game_state, game_state.active_player)
        active.lands_played_this_turn = 0
        # No priority in untap step; mana pools don't need clearing
        return game_state

    elif step == Step.UPKEEP:
        # CR 702.61c: At the beginning of your upkeep, remove a time counter from each
        # suspended card you own. When the last is removed, cast it for free.
        active = get_player(game_state, game_state.active_player)
        still_suspended = []
        for card in active.suspended_cards:
            tc_match = None
            if card.parse_status and card.parse_status.startswith("suspended:"):
                try:
                    tc_match = int(card.parse_status.split(":")[1])
                except (ValueError, IndexError):
                    tc_match = 0
            remaining = (tc_match or 0) - 1
            if remaining <= 0:
                # Cast for free — TASK-019-026: auto-cast suspended card
                logger.info("Suspend: %s time counters exhausted — casting for free", card.name)
                from mtg_engine.engine.stack import cast_spell
                
                # Add card to hand temporarily so cast_spell can find it
                ready = card.model_copy(update={"parse_status": "ok"})
                active.hand.append(ready)
                
                try:
                    # Cast with empty mana payment (it's free under suspend)
                    game_state = cast_spell(
                        game_state,
                        game_state.active_player,
                        ready.id,
                        targets=[],
                        mana_payment={}
                    )
                    # If it's a creature, grant haste (TASK-019-027)
                    if "creature" in ready.type_line.lower():
                        # Mark that haste should be granted when creature enters
                        # This is handled in put_permanent_onto_battlefield via metadata
                        for stack_obj in game_state.stack:
                            if stack_obj.source_card.id == ready.id:
                                if not stack_obj.metadata:
                                    stack_obj.metadata = {}
                                stack_obj.metadata["grant_haste"] = True
                                break
                except ValueError as e:
                    # If cast fails, put it back on suspended_cards
                    active.hand[:] = [c for c in active.hand if c.id != ready.id]
                    still_suspended.append(card)
                    logger.debug("Suspend cast failed for %s: %s", card.name, e)
            else:
                updated = card.model_copy(update={"parse_status": f"suspended:{remaining}"})
                still_suspended.append(updated)
                logger.debug("Suspend: %s now has %d time counter(s)", card.name, remaining)
        active.suspended_cards = still_suspended

        # US14 (T033): Saga upkeep — increment lore counter and queue chapter ability
        from mtg_engine.models.game import PendingTrigger
        import uuid as _uuid
        import re as _re_saga
        _ROMAN_MAX = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
                      6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X"}
        for perm in list(game_state.battlefield):
            if perm.controller != game_state.active_player:
                continue
            if "saga" not in perm.card.type_line.lower():
                continue
            # Increment lore counter
            current_lore = perm.counters.get("lore", 0) + 1
            perm.counters["lore"] = current_lore
            logger.debug("Saga upkeep: %s now has %d lore counter(s)", perm.card.name, current_lore)

            # Determine max chapters from oracle text
            oracle = perm.card.oracle_text or ""
            roman_nums = _re_saga.findall(r'\b(I{1,3}|IV|V|VI{0,3}|IX|X)\b(?:\s*[,—])', oracle)
            max_chapter = 0
            _ROMAN_TO_INT = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
                             "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}
            for r in roman_nums:
                max_chapter = max(max_chapter, _ROMAN_TO_INT.get(r, 0))
            if max_chapter == 0:
                max_chapter = 3  # default to 3 chapters if we can't parse

            from mtg_engine.engine.zones import _get_saga_chapter_text
            trigger = PendingTrigger(
                id=str(_uuid.uuid4()),
                source_permanent_id=perm.id,
                controller=perm.controller,
                trigger_type="saga_chapter",
                effect_description=f"Saga chapter {_ROMAN_MAX.get(current_lore, str(current_lore))}: {_get_saga_chapter_text(perm.card, current_lore)}",
                source_card_name=perm.card.name,
            )
            game_state.pending_triggers.append(trigger)

            # US14 (T034): Saga sacrifice logic — sacrifice after final chapter resolves
            if current_lore >= max_chapter:
                # Schedule a delayed trigger to sacrifice at next priority
                game_state.delayed_triggers.append({
                    "phase": game_state.phase.value,
                    "step": None,  # fire at next step change
                    "controller": perm.controller,
                    "effect": f"sacrifice_saga:{perm.id}",
                    "once": True,
                })
                logger.debug("Saga: %s at final chapter, sacrifice scheduled", perm.card.name)

        return game_state

    elif step == Step.DRAW:
        # REQ-T04: active player draws one card (first-player first-turn exception
        # is handled at game creation, not here)
        # US10: Check for dredge before drawing
        import re as _re_dredge
        player = get_player(game_state, game_state.active_player)
        dredgeable_cards = []
        
        # Check graveyard for cards with dredge ability
        if player.graveyard:
            _DREDGE_RE = _re_dredge.compile(r'[Dd]redge (\d+)', _re_dredge.IGNORECASE)
            for card in player.graveyard:
                dredge_match = _DREDGE_RE.search(card.oracle_text or "")
                if dredge_match:
                    dredge_n = int(dredge_match.group(1))
                    # Check if graveyard has enough cards to dredge
                    if len(player.graveyard) >= dredge_n:
                        dredgeable_cards.append((card, dredge_n))
        
        # If dredge is available, set pending dredge choice instead of drawing immediately
        if dredgeable_cards:
            game_state.pending_dredge_choice = {
                "player": game_state.active_player,
                "dredgeable_cards": [c[0] for c in dredgeable_cards],
                "dredge_numbers": {c[0].id: c[1] for c in dredgeable_cards},
            }
            # Return current game state without drawing
            return game_state
        
        # No dredge available, draw normally
        game_state, _ = draw_card(game_state, game_state.active_player)
        return game_state

    elif step == Step.FIRST_STRIKE_DAMAGE:
        # US3: Handle first-strike damage step
        # Apply first-strike damage to creatures with first strike or double strike
        from mtg_engine.engine.combat import assign_combat_damage
        game_state = assign_combat_damage(game_state, first_strike_only=True)
        # Run SBAs after first-strike damage resolution
        from mtg_engine.engine.sba import _check_once
        game_state, _ = _check_once(game_state)
        # Grant priority to active player
        game_state.priority_holder = game_state.active_player
        return game_state

    elif step == Step.COMBAT_DAMAGE:
        # US3: Handle regular combat damage step
        # Apply regular combat damage to creatures without first strike or double strike
        from mtg_engine.engine.combat import assign_combat_damage
        game_state = assign_combat_damage(game_state, first_strike_only=False)
        # Run SBAs after regular damage resolution
        from mtg_engine.engine.sba import _check_once
        game_state, _ = _check_once(game_state)
        # Grant priority to active player
        game_state.priority_holder = game_state.active_player
        return game_state

    # US18: Check delayed triggers — move matching ones into pending_triggers (CR 603.7)
    if game_state.delayed_triggers:
        from mtg_engine.models.game import PendingTrigger
        import uuid as _uuid
        current_phase = game_state.phase.value
        current_step = game_state.step.value
        still_pending = []
        for dt in game_state.delayed_triggers:
            phase_match = dt.get("phase") == current_phase
            step_val = dt.get("step")
            step_match = step_val is None or step_val == current_step
            if phase_match and step_match:
                trigger = PendingTrigger(
                    id=str(_uuid.uuid4()),
                    source_permanent_id="delayed",
                    controller=dt["controller"],
                    trigger_type="delayed",
                    effect_description=dt["effect"],
                    source_card_name="delayed_trigger",
                )
                game_state.pending_triggers.append(trigger)
                logger.info("Delayed trigger fires for %s at %s/%s", dt["controller"], current_phase, current_step)
                if not dt.get("once", True):
                    still_pending.append(dt)
            else:
                still_pending.append(dt)
        game_state.delayed_triggers = still_pending

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

    # CR 511.3: Clear combat state when leaving the End of Combat step.
    # Without this, old attackers persist into the next turn and deal damage again.
    if current == (Phase.COMBAT, Step.END_OF_COMBAT):
        from mtg_engine.engine.combat import end_combat as _end_combat
        game_state = _end_combat(game_state)

    try:
        idx = TURN_SEQUENCE.index(current)
    except ValueError:
        logger.warning("Current (phase, step) not in TURN_SEQUENCE: %s; resetting to index 0", current)
        idx = -1

    if idx + 1 < len(TURN_SEQUENCE):
        next_phase, next_step = TURN_SEQUENCE[idx + 1]
        # US7: Phase skip — skip entire phase if phase_skip_flags[phase_name] is True
        if game_state.phase_skip_flags.get(next_phase.value, False):
            # Clear the skip flag and skip all steps in this phase
            game_state.phase_skip_flags.pop(next_phase.value, None)
            # Find the last step of this phase and advance past it
            last_phase_idx = idx + 1
            while (
                last_phase_idx + 1 < len(TURN_SEQUENCE)
                and TURN_SEQUENCE[last_phase_idx + 1][0] == next_phase
            ):
                last_phase_idx += 1
            if last_phase_idx + 1 < len(TURN_SEQUENCE):
                next_phase, next_step = TURN_SEQUENCE[last_phase_idx + 1]
            else:
                game_state = _advance_turn(game_state)
                game_state = begin_step(game_state)
                if game_state.step != Step.UNTAP:
                    game_state.priority_holder = game_state.active_player
                return game_state
            logger.info("Phase %s skipped via phase_skip_flags", next_phase.value)
        game_state.phase = next_phase
        game_state.step = next_step
        # Reset per-step flags when advancing steps
        if game_state.combat is not None:
            game_state.combat.damage_assigned = False
            game_state.combat.blockers_declared = False
    else:
        # End of turn — advance to next player's turn
        game_state = _advance_turn(game_state)

    game_state = begin_step(game_state)

    # Grant priority to active player (except untap step — no priority there). REQ-S01
    if game_state.step != Step.UNTAP:
        game_state.priority_holder = game_state.active_player

    return game_state


def _advance_turn(game_state: GameState) -> GameState:
    """Switch to the next player's turn, consuming extra turns first (CR 500.7)."""
    # CR 500.7: extra turns form a LIFO stack — pop() gives the next extra turn recipient
    if game_state.extra_turns:
        next_player = game_state.extra_turns.pop()
        logger.info("Extra turn begins for %s (remaining extra turns: %d)",
                    next_player, len(game_state.extra_turns))
    else:
        next_player = _other_player(game_state)
    game_state.active_player = next_player
    game_state.priority_holder = next_player
    game_state.turn += 1
    game_state.phase = Phase.BEGINNING
    game_state.step = Step.UNTAP
    # Clear phase skip flags at end of turn
    game_state.phase_skip_flags.clear()
    logger.info("Turn %d begins; active player: %s", game_state.turn, game_state.active_player)
    return game_state


def process_cleanup_step(game_state: GameState) -> GameState:
    """
    Process the cleanup step per CR 514.
    
    Actions:
    1. Discard to hand size: if active player's hand > max_hand_size, set pending_discard_choice
    2. Remove damage: iterate battlefield, reset damage_marked = 0 on all permanents
    3. Expire "until end of turn" effects: reset power_bonus, toughness_bonus where expires == "end_of_turn";
       clear crewed_until_end_of_turn
    4. Priority check: call check_sba() and check_triggers(); if anything fires, set priority and loop back
    
    Returns GameState with pending choices set or priority granted for further processing.
    """
    from mtg_engine.engine.zones import get_player
    from mtg_engine.engine.sba import _check_once
    
    active = get_player(game_state, game_state.active_player)
    
    # 1. Discard to hand size
    if len(active.hand) > active.max_hand_size:
        from mtg_engine.models.game import PendingTrigger
        import uuid as _uuid
        
        excess_cards = active.hand[active.max_hand_size:]
        game_state.pending_discard_choice = {
            "player": game_state.active_player,
            "cards": excess_cards,
        }
        logger.info("Cleanup: %s has %d cards (max %d), setting discard choice",
                   game_state.active_player, len(active.hand), active.max_hand_size)
    
    # 2. Remove damage from all permanents
    for perm in game_state.battlefield:
        perm.damage_marked = 0
    
    # 3. Expire "until end of turn" effects
    for perm in game_state.battlefield:
        # Clear power/toughness bonuses expiring at end of turn
        if perm.power_bonus_expires == "end_of_turn":
            perm.power_bonus = 0
            perm.power_bonus_expires = None
        if perm.toughness_bonus_expires == "end_of_turn":
            perm.toughness_bonus = 0
            perm.toughness_bonus_expires = None
        
        # Clear crew status
        if perm.crewed_until_end_of_turn:
            perm.crewed_until_end_of_turn = False
            # Remove "Creature" from type_line
            if "creature" in perm.card.type_line.lower():
                # Already a creature, no change needed
                pass
            else:
                # Remove creature type
                words = perm.card.type_line.split()
                new_words = [w for w in words if w.lower() != "creature"]
                perm.card = perm.card.model_copy(update={
                    "type_line": " ".join(new_words),
                })
    
    # 4. Check SBAs and triggers - if anything fires, we need to loop back
    game_state, sba_fired = _check_once(game_state)
    
    # Check for triggers (simplified - just check if pending_triggers has anything)
    trigger_fired = len(game_state.pending_triggers) > 0
    
    if sba_fired or trigger_fired:
        # Grant priority to active player and loop back to cleanup
        logger.info("Cleanup: SBA/triggers fired, granting priority to %s", game_state.active_player)
        game_state.priority_holder = game_state.active_player
        # Note: The game loop should call process_cleanup_step again if pending choices exist
        # or advance_step when both players pass
    else:
        # No SBAs or triggers - grant priority to move to end step
        game_state.priority_holder = game_state.active_player
    
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
