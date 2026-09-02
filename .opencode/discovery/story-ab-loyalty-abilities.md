# Story: Loyalty Abilities (CR 606)

## User Story
As a game engine developer, I want the loyalty ability system to function correctly per the Comprehensive Rules, so that planeswalker cards with loyalty abilities (written as "[+N], [-N], or [0]: [effect]") work according to the rules.

## Context
Loyalty abilities are a special type of activated ability found on planeswalker cards. The activation cost is always a loyalty symbol: [+N] (add N loyalty counters), [-N] (remove N loyalty counters), or [0] (no change). Per CR 606.1, these are written in the format "[+N], [-N], or [0]: [effect]." and can only be activated once per turn per planeswalker, and only as a sorcery.

Key rules:
- **Once per turn**: Each planeswalker can only have one loyalty ability activated per turn (CR 606.3)
- **Sorcery speed**: Can only be activated when the player could cast a sorcery (CR 606.3)
- **Cost is the loyalty change**: The [+N]/[-N]/[0] is the activation cost — placing or removing counters from the planeswalker
- **Cannot activate if insufficient counters**: If the cost is [-N] and the planeswalker has fewer than N loyalty counters, it cannot be activated (CR 606.4)
- **Multiple planeswalkers**: Each planeswalker on the battlefield tracks its own once-per-turn usage
- **Loyalty abilities are activated abilities**: They follow all normal activated ability rules except as modified by CR 606

### Comprehensive Rules Grounding
- **CR 606.1**: "A loyalty ability is an activated ability whose activation cost includes a '[+N]', '[-N]', or '[0]' symbol on a planeswalker."
- **CR 606.3**: "A player may activate a loyalty ability of a permanent they control only during a main phase, only while the stack is empty, and only once per turn."
- **CR 606.4**: "A loyalty ability with a negative loyalty cost can't be activated unless the permanent has at least that many loyalty counters on it."
- **CR 606.5**: "The cost to activate a loyalty ability is to put the appropriate number of loyalty counters on or remove the appropriate number of loyalty counters from the permanent."
- **Example card**: Jace, the Mind Sculptor — "+2: Look at the top card of target player's library... / 0: Draw three cards, then put two cards from your hand on top of your library... / −1: Return target creature to its owner's hand..."

## Acceptance Criteria
- [x] `parse_loyalty_ability(text: str) -> LoyaltyAbility | None` extracts loyalty cost ([+N]/[-N]/[0]) and effect text
- [x] `get_possible_loyalty_abilities(gs, perm_id) -> list[LoyaltyAbility]` returns all loyalty abilities a planeswalker can activate (considering loyalty counter sufficiency for negative costs)
- [x] Once-per-turn tracking: `GameState.planeswalker_activations: dict[str, int]` tracks which planeswalkers have used their loyalty ability each turn
- [x] `can_activate_loyalty(gs, perm_id, player_name) -> bool` checks: main phase, stack empty, once-per-turn, sufficient counters for negative costs
- [x] `activate_loyalty(gs, perm_id, ability_index, player_name) -> GameState` applies the loyalty counter change (cost) and queues the effect for stack resolution via pure `model_copy(update=...)` transform
- [x] AI auto-resolution: bot planeswalker activation priority (e.g., + abilities when defensive, - abilities when advantageous)
- [x] Human path: queues `pending_loyalty_choice` on GameState for API pick
- [x] Full regression passes

## Dependencies
- story-ab-activated-abilities.md (loyalty abilities are a subtype of activated abilities)

## Status: ✅ Complete

Implemented: `ability/loyalty.py` (285 lines) with `LoyaltyAbilityTracker`, `can_activate_loyalty()` (main phase, stack empty, once-per-turn), `activate_loyalty_ability()`. API endpoint `POST /game/{game_id}/activate-loyalty`. Legal actions computed at `game.py:3263-3284`. Loyalty counter management, SBA for 0 loyalty (sba.py:207-215), combat damage to planeswalkers (combat/core.py:634-639).

## Priority: High

## Notes
- Planeswalker uniqueness rule (CR 306.4) is handled separately — this story only covers loyalty ability activation.
- Loyalty abilities are sorcery-speed by default per CR 606.3, but this can be modified by other effects (e.g., Teferi, Time Raveler's static ability).
- The engine may need to track planeswalker activations per planeswalker per turn. A dict of `perm_id → boolean` (reset at end of turn) is the simplest approach.
- Forge reference: `LoyaltyAbility` class with `getLoyaltyAbilityList()` on Planeswalker cards.
