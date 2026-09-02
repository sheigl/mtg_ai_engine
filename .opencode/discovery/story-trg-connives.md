# Story: Connives Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a connives trigger pattern with check function and engine wiring, so that cards with "When ~ connives" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Connive" is a keyword from Streets of New Capenna (SNC) where a creature draws a card, then discards a card, and if a nonland card was discarded, it gets a +1/+1 counter.

### Comprehensive Rules Grounding
- **CR 702.XX**: "To connive, a player draws a card, then discards a card. If they discarded a nonland card this way, they put a +1/+1 counter on a creature that connived."
- **Example card**: *Tenacious Underdog* — "When Tenacious Underdog connives, it deals damage equal to its power to target creature."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into connive keyword resolution flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Connive triggers fire when a creature successfully connives (draw + discard cycle completes).
- The trigger should fire regardless of whether a nonland card was discarded (the +1/+1 counter component is separate).
- Example cards: *Tenacious Underdog*, *Raffine, Scheming Seer*, *Obscura Interceptor*, *Workshop Warchief*.
