# Story: Flipped Coin Trigger (CR 701.24)

## User Story
As an MTG engine developer, I want a flipped coin trigger pattern so that cards with "whenever you flip a coin" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 701.24**: "A coin may be flipped any time a spell, ability, or rule calls for it to be flipped. If a player wins the flip, that player may choose to have the coin land on either side. If a player loses the flip, the other player may choose to have the coin land on either side."
- **Example card**: Frenetic Efreet — "Flip a coin: If you win the flip, exile Frenetic Efreet and return it to the battlefield under its owner's control. If you lose the flip, sacrifice it."

## Acceptance Criteria
- [ ] Add `FLIPPED_COIN_TRIGGER_PATTERNS` regex patterns for "whenever you flip a coin" and "whenever a player flips a coin"
- [ ] Add `check_flipped_coin_triggers()` check function
- [ ] Wire into the engine coin flip resolution path
- [ ] Integration tests with a card that triggers on coin flip
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M
