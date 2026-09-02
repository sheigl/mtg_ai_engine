# Story: Become Renowned Trigger (CR 702.81)

## User Story
As an MTG engine developer, I want a become-renowned trigger pattern with check function and engine wiring, so that cards with "When ~ becomes renowned" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Renowned" is a keyword from Magic Origins where a creature deals combat damage to a player and becomes renowned.

### Comprehensive Rules Grounding
- **CR 702.81**: "Renown is a triggered ability. 'Renown N' means 'Whenever this creature deals combat damage to a player, if it isn't renowned, put N +1/+1 counters on it and it becomes renowned.'"
- **Example card**: *Relic Seeker* — "When Relic Seeker becomes renowned, you may search your library for an Equipment card, reveal it, put it into your hand, then shuffle."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into renown keyword resolution flow in combat damage
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Renown fires when combat damage is dealt to a player by a creature with renown, and the creature was not already renowned.
- The trigger only fires once per creature — after it becomes renowned, dealing subsequent combat damage does not re-fire.
- Example cards: *Relic Seeker*, *Knight of the Pilgrim's Road*, *Aerial Volley*.
