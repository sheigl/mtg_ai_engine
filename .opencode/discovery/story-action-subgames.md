# Story: Subgames (CR 716)

## User Story
As a game engine developer, I want subgames to function correctly per the Comprehensive Rules, so that cards like Shahrazad can create a complete nested Magic game within the main game.

## Context
Subgames are a rare (one card: Shahrazad) and officially deprecated mechanic that creates a complete Magic game within the main game. The subgame is played with its own starting life totals, library, and turn structure. The winner of the subgame gets a reward (Shahrazad's effect: winner gains 5 life).

### Comprehensive Rules Grounding
- **CR 716.1**: "Some cards involve subgames, which are complete Magic games played within the main game."
- **CR 716.2**: "The subgame uses the same decks as the main game. Each player starts with 20 life in the subgame."
- **CR 716.3**: "The subgame is played with the same players. The player who started the subgame takes the first turn."
- **CR 716.4a**: "A player can't play a card named Shahrazad during a subgame."
- **CR 716.5**: "When a player wins a subgame, they are considered to have won the subgame (not the main game)."
- **CR 716.6**: "Permanents and cards from the subgame do not return to the main game after the subgame ends."
- **CR 716.7**: "All cards in the subgame are removed from the main game; after the subgame ends, they are put into exile."
- **Example card**: Shahrazad — "Players play a subgame. The winner of the subgame gains 5 life."

## Acceptance Criteria
- [ ] `start_subgame(gs, player_name)` creates a new nested game state
- [ ] The subgame is a complete Magic game with 20 starting life
- [ ] The starting player of the subgame is the player who started it
- [ ] Shahrazad cannot be played within a subgame (CR 716.4a)
- [ ] Cards in the subgame are removed from the main game
- [ ] When subgame ends, all subgame cards are put into exile in the main game
- [ ] Winner of the subgame gains the reward (e.g., 5 life for Shahrazad)
- [ ] Main game resumes from where it was paused
- [ ] Integration test: start a subgame, play it to completion, verify reward
- [ ] Integration test: players cannot use cards from subgame in main game
- [ ] Integration test: subgame cards exiled to main game after subgame ends
- [ ] Full regression suite passes

## Dependencies
- Full game engine (subgames are complete games)
- This is a very isolated, low-priority mechanic

## Priority: Low
## Status: ❌ Not Implemented

> **Gap**: No subgames implementation.

## Estimated Effort: L
