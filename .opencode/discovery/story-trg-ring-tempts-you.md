# Story: Ring Tempts You Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a Ring-tempts-you trigger pattern so that Lord of the Rings cards with "whenever the Ring tempts you" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR TBD**: "The Ring tempts you" is a mechanic from the Lord of the Rings: Tales of Middle-earth set that tracks a player's ring bearer and eminence level.
- **Example card**: Various LOTR cards — "Whenever the Ring tempts you, draw a card."

## Acceptance Criteria
- [ ] Add `RING_TEMPTS_YOU_TRIGGER_PATTERNS` regex patterns for "whenever the Ring tempts you" and "when the Ring tempts you"
- [ ] Add `check_ring_tempts_you_triggers()` check function
- [ ] Wire into the engine Ring-tempts-you resolution path
- [ ] Integration tests with a card that triggers on the Ring tempting you
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M
