# Story: Investigate (CR 701.32)

## User Story
As a game engine developer, I want the investigate action to function correctly per the Comprehensive Rules, so that players can create Clue tokens which can later be sacrificed to draw cards.

## Context
Investigate creates a Clue artifact token. Clue tokens are colorless, have "{2}, Sacrifice this artifact: Draw a card." as an activated ability, and are artifacts. Investigate is a keyword action written as "investigate" in rules text.

### Comprehensive Rules Grounding
- **CR 701.32a**: "To investigate, create a Clue token."
- **CR 701.32b**: "Clue tokens are colorless artifact tokens with '{2}, Sacrifice this artifact: Draw a card.'"
- **CR 701.32c**: "If an effect refers to a Clue, it means any Clue artifact, not just a Clue token."
- **CR 110.5c**: "A token is subject to anything that affects permanents in general."
- **Example card**: Tireless Tracker — "Landfall — Whenever a land enters under your control, investigate."
- **Example card**: Search the Premises — "Whenever a creature attacks you or a planeswalker you control, investigate."

## Acceptance Criteria
- [ ] `investigate(gs, player_name)` creates a Clue token under the player's control
- [ ] Clue token is a colorless artifact token with name "Clue"
- [ ] Clue token has activated ability: "{2}, Sacrifice this artifact: Draw a card."
- [ ] Clue token is tracked as a token permanent (with `is_token=True`)
- [ ] Multiple investigates create multiple Clue tokens
- [ ] Clue token can be sacrificed to draw a card (cost: {2} + sacrifice)
- [ ] The sacrifice/draw ability follows normal activated ability rules
- [ ] "Whenever you investigate" triggers fire when a Clue is created
- [ ] Integration test: investigate creates a Clue token on battlefield
- [ ] Integration test: sacrifice Clue token, pay {2}, draw a card
- [ ] Integration test: multiple investigates create multiple tokens
- [ ] Full regression suite passes

## Dependencies
- Token creation rules (story-rule-tokens.md)
- Activated abilities (story-action-activate-ability.md)

## Priority: High
## Status: ❌ Not Implemented

> **Gap**: No `investigate()` function, no Clue token creation logic. `investigate` only appears in keyword list parsing — no actual card generation.

## Estimated Effort: M
