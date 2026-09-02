"""
Planeswalker loyalty ability system.

ACT-03: Handles loyalty counter management, ability activation, and
the rule that a planeswalker's loyalty ability can only be activated
once per turn.

CR 606: Planeswalkers.
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent, Card

logger = logging.getLogger(__name__)


class LoyaltyAbilityTracker:
    """
    Tracks which planeswalkers have had loyalty abilities activated
    this turn. A loyalty ability can only be activated once per turn
    per planeswalker. CR 606.3.
    """

    def __init__(self):
        # Set of permanent IDs that have activated a loyalty ability this turn
        self._activated_this_turn: set[str] = set()
        self._turn_number: int = 0

    def new_turn(self, turn_number: int) -> None:
        """Reset tracking at the start of a new turn."""
        if turn_number != self._turn_number:
            self._activated_this_turn.clear()
            self._turn_number = turn_number

    def has_activated_this_turn(self, perm_id: str) -> bool:
        """Check if this planeswalker has activated a loyalty ability this turn."""
        return perm_id in self._activated_this_turn

    def mark_activated(self, perm_id: str) -> None:
        """Mark that this planeswalker has activated a loyalty ability."""
        self._activated_this_turn.add(perm_id)


# Global tracker instance
_loyalty_tracker = LoyaltyAbilityTracker()


def get_loyalty_tracker() -> LoyaltyAbilityTracker:
    """Get the global loyalty ability tracker."""
    return _loyalty_tracker


def reset_loyalty_tracker() -> None:
    """Reset the loyalty tracker (for testing)."""
    global _loyalty_tracker
    _loyalty_tracker = LoyaltyAbilityTracker()


def can_activate_loyalty(
    game_state: GameState,
    perm: Permanent,
    controller: str,
    loyalty_change: int,
) -> bool:
    """
    Check if a loyalty ability can be activated.

    CR 606.3: A player may activate a loyalty ability of a permanent
    they control any time they have priority and the stack is empty
    during a main phase of their turn.

    CR 606.3a: Each time a player activates a loyalty ability of a
    planeswalker they control, they put the appropriate number of
    loyalty counters on it.

    Args:
        game_state: Current game state.
        perm: The planeswalker permanent.
        controller: Player trying to activate.
        loyalty_change: The loyalty cost (+N, -N, or 0).

    Returns:
        True if the ability can be activated.
    """
    # Must control the planeswalker
    if perm.controller != controller:
        return False

    # Must be your main phase
    if game_state.phase.value not in ("precombat_main", "postcombat_main"):
        return False

    # Must be active player
    if controller != game_state.active_player:
        return False

    # Stack must be empty
    if game_state.stack:
        return False

    # Can't activate if already activated this turn
    tracker = get_loyalty_tracker()
    if tracker.has_activated_this_turn(perm.id):
        return False

    # Can't pay negative loyalty if not enough counters
    if loyalty_change < 0:
        current_loyalty = perm.counters.get("loyalty", 0)
        if current_loyalty + loyalty_change < 0:
            return False

    return True


def activate_loyalty_ability(
    game_state: GameState,
    perm: Permanent,
    controller: str,
    loyalty_change: int,
    effect: str,
) -> GameState:
    """
    Activate a loyalty ability: pay the loyalty cost and execute the effect.

    Args:
        game_state: Current game state.
        perm: The planeswalker permanent.
        controller: Player activating the ability.
        loyalty_change: The loyalty cost (+N, -N, or 0).
        effect: The effect text to execute.

    Returns:
        Modified game state.
    """
    if not can_activate_loyalty(game_state, perm, controller, loyalty_change):
        raise ValueError(
            f"{controller} cannot activate loyalty ability on {perm.card.name}"
        )

    # Pay the loyalty cost
    current = perm.counters.get("loyalty", 0)
    perm.counters["loyalty"] = current + loyalty_change

    # Mark as activated this turn
    tracker = get_loyalty_tracker()
    tracker.mark_activated(perm.id)

    logger.info(
        "%s activated %s loyalty ability (%s, loyalty now %d)",
        controller,
        perm.card.name,
        loyalty_change,
        perm.counters["loyalty"],
    )

    # Execute the effect — pure transform returns new GameState
    game_state = _execute_loyalty_effect(game_state, perm, controller, effect)

    return game_state


def _execute_loyalty_effect(
    game_state: GameState,
    perm: Permanent,
    controller: str,
    effect: str,
) -> GameState:
    """
    Execute the effect portion of a loyalty ability. Pure transform.

    This is a simplified implementation that handles common effect patterns.
    Full implementation would integrate with the effect system.
    """
    lower = effect.lower()

    # Draw cards
    if "draw" in lower:
        import re as _re
        match = _re.search(r"draw\s+(\d+)\s+card", effect, _re.IGNORECASE)
        count = int(match.group(1)) if match else 1
        player = next((p for p in game_state.players if p.name == controller), None)
        if player:
            from mtg_engine.engine.zones import draw_card as _draw_card
            for _ in range(count):
                game_state, _ = _draw_card(game_state, controller)

    # Gain life
    elif "gain" in lower and "life" in lower:
        import re as _re
        match = _re.search(r"gain\s+(\d+)\s+life", effect, _re.IGNORECASE)
        amount = int(match.group(1)) if match else 1
        new_players = []
        for p in game_state.players:
            if p.name == controller:
                new_players.append(p.model_copy(update={"life": p.life + amount}))
            else:
                new_players.append(p)
        game_state = game_state.model_copy(update={"players": new_players})

    # Deal damage
    elif "damage" in lower:
        import re as _re
        match = _re.search(r"(\d+)\s+damage", effect, _re.IGNORECASE)
        amount = int(match.group(1)) if match else 1
        # Simplified: deal to first opponent — pure transform
        new_players = []
        damage_dealt = False
        for p in game_state.players:
            if not damage_dealt and p.name != controller:
                new_players.append(p.model_copy(update={"life": p.life - amount}))
                damage_dealt = True
            else:
                new_players.append(p)
        game_state = game_state.model_copy(update={"players": new_players})

    # Create token
    elif "create" in lower and "token" in lower:
        from mtg_engine.engine.zones import put_permanent_onto_battlefield as _put_perm
        from mtg_engine.models.game import Card as _Card
        player = next((p for p in game_state.players if p.name == controller), None)
        if player:
            token = _Card(
                name=f"{perm.card.name} Token",
                type_line="Creature — Soldier",
                power="1",
                toughness="1",
                colors=perm.card.colors,
            )
            game_state, _ = _put_perm(game_state, token, controller, is_token=True)
            # Wire: Token Trigger (CR 704.5c) — check_token_triggers is the single
            # owner of token triggers (the zone listener skips them).
            from mtg_engine.engine.triggers import check_token_triggers as _check_token
            game_state = _check_token(game_state, controller)

    # Generic fallback
    else:
        logger.debug(
            "Loyalty effect not yet implemented: %s", effect
        )

    return game_state


def set_initial_loyalty(perm: Permanent, card: Card) -> None:
    """
    Set a planeswalker's initial loyalty when it enters the battlefield.

    CR 606.2: As a planeswalker enters, its controller puts a number
    of loyalty counters equal to its loyalty printed on it onto it.
    """
    if card.loyalty:
        try:
            perm.counters["loyalty"] = int(card.loyalty)
        except (ValueError, TypeError):
            perm.counters["loyalty"] = 0
    else:
        perm.counters["loyalty"] = 0


def get_current_loyalty(perm: Permanent) -> int:
    """Get the current loyalty of a planeswalker."""
    return perm.counters.get("loyalty", 0)


def check_loyalty_death(
    game_state: GameState,
    perm: Permanent,
) -> GameState:
    """
    Check if a planeswalker should be put in its owner's graveyard
    due to 0 or less loyalty. CR 606.5.

    Args:
        game_state: Current game state.
        perm: The planeswalker permanent to check.

    Returns:
        Modified game state.
    """
    loyalty = get_current_loyalty(perm)
    if loyalty <= 0:
        player = next(
            (p for p in game_state.players if p.name == perm.controller),
            None,
        )
        if player:
            player.graveyard.append(perm.card)
        game_state.battlefield = [
            p for p in game_state.battlefield if p.id != perm.id
        ]
        logger.info(
            "%s put in graveyard due to 0 loyalty", perm.card.name
        )
    return game_state
