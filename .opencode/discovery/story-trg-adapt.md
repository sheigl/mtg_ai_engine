# Story: Adapt Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want an adapt trigger pattern with check function and engine wiring, so that cards with "Whenever ~ adapts" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Adapt" is a +1/+1 counter mechanic from Ravnica Allegiance where creatures enter with a number of +1/+1 counters.

### Comprehensive Rules Grounding
- **CR 702.XX**: "Adapt N means 'If this permanent has no +1/+1 counters on it, put N +1/+1 counters on it.'"
- **Example card**: *Pteramander* — "Adapt {U} ({U}: If this creature has no +1/+1 counters on it, put a +1/+1 counter on it.)"

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into adapt keyword resolution flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Adapt triggers are relatively rare but exist in Ravnica Allegiance and RNA-related sets.
- The trigger fires when a creature adapts (gets +1/+1 counters as a result of the adapt keyword activation).
- Must distinguish adapt counter placement from other +1/+1 counter sources.
