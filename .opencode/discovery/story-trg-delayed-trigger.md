# Story: Delayed Trigger Framework (CR 603.7)

## User Story
As an MTG engine developer, I want a general delayed trigger framework so that cards that create "when [condition], do [effect]" delayed triggers (e.g., "At the beginning of the next end step, sacrifice this creature") fire correctly.

## Comprehensive Rules Grounding
- **CR 603.7**: "A delayed triggered ability is a triggered ability that is created by a resolving spell or ability. It triggers when a specified event occurs and lasts for a specified duration."
- **Example card**: "Exile target creature. At the beginning of the next end step, return it to the battlefield under its owner's control." (e.g., Swords to Plowshares variantly "exile then return")

## Acceptance Criteria
- [ ] Design and implement a delayed trigger data structure (DelayedTrigger model or similar)
- [ ] Add `GameState.delayed_triggers: list[DelayedTrigger]` field
- [ ] Add `DELAYED_TRIGGER_PATTERNS` regex patterns for "at the beginning of the next [phase/step]" and "when [event], [effect]" construction
- [ ] Add `check_delayed_triggers()` check function
- [ ] Wire into the engine phase/step path so delayed triggers fire at the right time
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: L
