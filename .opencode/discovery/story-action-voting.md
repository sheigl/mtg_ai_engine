# Story: Voting (CR 701.23)

## User Story
As a game engine developer, I want the voting action to function correctly per the Comprehensive Rules, so that cards that instruct players to vote (e.g., "Will of the Council") resolve correctly with votes being cast and counted.

## Context
Voting is a keyword action used in multiplayer-focused sets (Conspiracy, Commander Legends). Players vote on choices presented by the card. "Will of the Council" means that each player votes, starting with the controller of the spell/ability (or a specified player), and the outcome is determined by the majority vote.

### Comprehensive Rules Grounding
- **CR 701.23a**: "Some cards instruct players to vote. Voting is a keyword action."
- **CR 701.23b (Voting)**: "Starting with the player specified by the spell or ability, each player votes for one of the listed options."
- **CR 701.23c (Will of the Council)**: "Each player votes, starting with you (the controller)."
- **CR 701.23d**: "Each vote is cast in turn order."
- **CR 701.23e**: "The winning option is determined by which option received the most votes."
- **CR 701.23f**: "In case of a tie, the controller of the spell/ability chooses among the tied options."
- **CR 701.23g**: "Abilities that trigger 'whenever you vote' trigger when you finish voting."
- **Example card**: Council's Judgment — "Will of the council — Starting with you, each player votes for a nonland permanent you don't control. Exile the permanent with the most votes or tied for most votes."
- **Example card**: Magister of Worth — "Will of the council — Each player votes for 'death' or 'life.'"

## Acceptance Criteria
- [ ] `vote(gs, spell_controller, options, voters)` initiates voting
- [ ] Voting proceeds in turn order starting from the specified player
- [ ] Each voter chooses one of the available options
- [ ] For human players: queue `pending_vote_choice` with available options
- [ ] For AI players: auto-vote based on game state strategy
- [ ] The winning option is the one with the most votes
- [ ] Tie-breaking: spell/ability controller chooses among tied options
- [ ] "Whenever you vote" triggers fire for each player after they vote
- [ ] "Whenever you vote for X" triggers (more specific) fire for matching votes
- [ ] Integration test: 3-player vote, majority wins
- [ ] Integration test: tied vote — controller breaks the tie
- [ ] Integration test: vote triggers fire for each voter
- [ ] Full regression suite passes

## Dependencies
- Multiplayer turn order (story-turn-priority-system.md)
- Trigger system (vote triggers — story-trg-vote.md)

## Priority: Medium
## Status: ❌ Not Implemented

> **Gap**: No voting implementation.

## Estimated Effort: M
