# Story: Learn (CR 701.42)

## User Story
As a game engine developer, I want the learn action to function correctly per the Comprehensive Rules, so that players can either get a card from outside the game (sideboard) or discard a card to draw a card (loot).

## Context
Learn is a keyword action from the Strixhaven set. It offers a modal choice: either (a) take a card from sideboard and put it into hand, or (b) discard a card, then draw a card (loot). If the player chooses option (a) but has no sideboard, they cannot choose that option — they must loot. Learn is used primarily in digital but has paper implementations.

### Comprehensive Rules Grounding
- **CR 701.42a**: "To learn, choose a card you own from outside the game and put it into your hand, or discard a card, then draw a card."
- **CR 701.42b**: "If you choose to get a card from outside the game but you don't have a sideboard or your sideboard is empty, you discard and draw instead."
- **CR 701.42c**: "Learn does nothing if you choose the first option but have no cards outside the game."
- **Example card**: "When this creature enters, learn."
- **Example card**: Academic Dispute — "Target creature gets -2/-0 until end of turn. Learn."
- **See also**: Lesson cards (cards you can "learn" from sideboard)

## Acceptance Criteria
- [ ] `learn(gs, player_name)` offers two choices: fetch from sideboard or loot
- [ ] Option A: take a card from sideboard (outside the game) into hand
- [ ] Option B: discard a card, then draw a card (loot)
- [ ] For human players: queue `pending_learn_choice` with sideboard cards visible
- [ ] For AI players: auto-resolve — prefer fetch from sideboard if useful cards exist
- [ ] If sideboard is empty or unavailable, only loot option is valid
- [ ] "Whenever you learn" triggers fire after the action resolves
- [ ] The fetched card comes from the player's sideboard (for tournament play) or collection
- [ ] Integration test: learn with sideboard — fetch a card, it goes to hand
- [ ] Integration test: learn without sideboard — discard + draw instead
- [ ] Integration test: learn with no cards in hand — cannot loot, must fetch if possible
- [ ] Integration test: learn trigger fires
- [ ] Full regression suite passes

## Dependencies
- Sideboard zones (CR 100.4)
- Discard/draw mechanics
- Trigger system (learn triggers)

## Priority: Medium
## Status: ❌ Not Implemented

> **Gap**: No `learn()` function. Only appears in ability_parser.py keyword lists — no sideboard fetch or loot logic.

## Estimated Effort: M
