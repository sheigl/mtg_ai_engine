# Story: Mana Expend Trigger (CR 118.9)

## User Story
As an MTG engine developer, I want a mana-expend trigger pattern so that cards with "whenever you spend {mana}" abilities (distinct from generic mana-spent triggers) fire correctly.

## Comprehensive Rules Grounding
- **CR 118.9**: "Some triggered abilities trigger whenever a player spends mana. These abilities may trigger on spending one or more mana of a specific type or color."
- **Example card**: "Whenever you spend {U} or {B}, you may have target player mill a card." (e.g., Psychic Network style effects)

## Acceptance Criteria
- [ ] Add `MANA_EXPEND_TRIGGER_PATTERNS` regex patterns for "whenever you spend {mana}" and "whenever you spend one or more {mana}"
- [ ] Add `check_mana_expend_triggers()` check function
- [ ] Wire into the engine mana payment/spending path (distinct from existing check_mana_spent_triggers which covers broader patterns)
- [ ] Integration tests with a card that triggers on spending specific mana types
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M
