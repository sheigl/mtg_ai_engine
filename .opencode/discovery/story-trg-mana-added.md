# Story: Mana Added Trigger (CR 502.4)

## User Story
As an MTG engine developer, I want a mana-added trigger pattern so that cards with "whenever you add {mana}" abilities fire correctly during mana production.

## Comprehensive Rules Grounding
- **CR 502.4**: "Some triggered abilities trigger whenever a player adds mana. These abilities may trigger on adding one or more mana of a specific type or color."
- **Example card**: "Whenever you add one or more {G}, draw a card." (e.g., Ghirapur Aether Grid style effects)

## Acceptance Criteria
- [ ] Add `MANA_ADDED_TRIGGER_PATTERNS` regex patterns for "whenever you add {mana}" and "whenever you add one or more {mana}"
- [ ] Add `check_mana_added_triggers()` check function
- [ ] Wire into the engine mana production path (separate from existing mana production triggers — this is about specific mana colors being added)
- [ ] Integration tests with a card that triggers on adding specific mana types
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M
