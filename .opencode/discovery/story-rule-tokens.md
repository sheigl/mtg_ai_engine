# Story: Token Rules (CR 110.5-110.8)

## User Story
As a game engine developer, I want token permanents to follow all CR 110 token rules — tokens cease to exist when they leave the battlefield, tokens can't be face-down, and tokens are owned by their controller — so that token interactions work correctly.

## Context
Tokens represent permanents on the battlefield that aren't represented by physical cards. They have unique rules: tokens are owned by their controller (CR 110.5), tokens cease to exist the moment they leave the battlefield (CR 110.7g), tokens can't be turned face-down (CR 110.6b), and tokens entering the battlefield trigger "enters the battlefield" triggers like any other permanent.

### Comprehensive Rules Grounding
- **CR 110.5**: "A token is a marker used to represent a permanent on the battlefield that isn't represented by a card."
- **CR 110.5a**: "A token is both a card and not a card — it can't be cast as a spell, it can't be returned to a player's hand, and it ceases to exist in any zone other than the battlefield."
- **CR 110.6b**: "A token can't be turned face-down."
- **CR 110.7g**: "If a token is in a zone other than the battlefield, it ceases to exist. This is a state-based action."
- **CR 110.8**: "A token's owner is the player who created it. A token's controller is the player who controls the permanent it represents."
- **Example card**: "Create two 1/1 white Soldier creature tokens" — the tokens follow these rules

## Acceptance Criteria
- [ ] Token objects have a `is_token: bool = True` field on Permanent
- [ ] Token ownership = controller (CR 110.8)
- [ ] SBA: tokens in non-battlefield zones cease to exist (CR 110.7g) — checked in SBA loop
- [ ] Token cannot be turned face-down (CR 110.6b) — face-down action blocked for tokens
- [ ] Token entering/exiting battlefield triggers "enters"/"leaves" triggers normally
- [ ] Token copy effects (e.g., "copy target token") create tokens with same characteristics
- [ ] Phased-out tokens don't cease to exist (phasing keeps them in the game)
- [ ] Token death triggers (e.g., "when this creature dies") fire before the token ceases to exist
- [ ] Tokens that would go to graveyard/exile/hand/library cease to exist as an SBA after triggers queue
- [ ] Integration tests cover: token created, token dies, token leaves battlefield, token can't be face-down, token in graveyard ceases to exist, token copy
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: State-Based Actions (CR 704) — token cessation is an SBA

## Priority: Medium

## Status: 🔄 Partial

### Gap Description
Permanent model has is_token field, tokens are created via put_permanent_onto_battlefield(is_token=True), SBA loop removes tokens from non-battlefield zones (CR 704.5d), and token death triggers work (afterlife/undying/persist). But missing: explicit CR 110.6b token-cant-be-face-down enforcement, token ownership tracking per CR 110.8, and comprehensive token rules integration tests.

## Estimated Effort: M

## Notes
- The engine already handles some token mechanics (afterlife creates tokens) — this story formalizes the CR 110 rules
- Token cessation (CR 110.7g) is an SBA, not an immediate event — this means triggers from token death/etc. are queued first
- Key timing nuance: when a token dies, triggers fire ("when this creature dies"), THEN the token ceases to exist as the next SBA
- Tokens have a "card" representation in the engine (they need a Card-like object for characteristics), but are NOT actual cards
- Copying a token creates another token, not a card
- Token creatures that have been temporarily exiled (e.g., by "Swords to Plowshares" replacement with phasing) might have edge cases
- The `is_token` field exists on the Permanent model already — this story adds the SBA enforcement
