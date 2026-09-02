# Story: Claim Prize Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a claim-prize trigger pattern with check function and engine wiring, so that cards with sticker/prize triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Claim prize" is a mechanic associated with sticker sheets and prize-awarding effects from Un-sets and certain silver-bordered cards.

### Comprehensive Rules Governing Stickers
- **CR 702.XX**: "To claim a prize, a player takes the top card of their prize deck and puts it into their hand. Prize cards are kept in a separate prize zone."
- **Example card**: *Prize Wall* — "Whenever you claim a prize, you may have Prize Wall become an artifact creature until end of turn."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into prize/sticker resolution flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Claim prize is primarily an Un-set mechanic (Unstable, Unfinity) and may also appear in acorn/silver-bordered cards.
- Lower priority for tournament-legal format support, but the pattern should exist for completeness.
- Ensure the trigger pattern does not interfere with normal prize mechanics.
