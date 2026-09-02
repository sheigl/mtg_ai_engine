# Story: Instant/Sorcery Cast Trigger (CR 601.2)

## User Story
As an MTG engine developer, I want an instant/sorcery-cast trigger pattern so that cards with "whenever you cast an instant or sorcery spell" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 601.2**: "To cast a spell is to take it from where it is (usually the hand), put it on the stack, and pay its costs."
- **Example card**: Guttersnipe — "Whenever you cast an instant or sorcery spell, Guttersnipe deals 2 damage to each opponent."

## Acceptance Criteria
- [ ] Add `INSTANT_SORCERY_CAST_TRIGGER_PATTERNS` regex patterns for "whenever you cast an instant or sorcery spell" and type-specific sub-patterns
- [ ] Add `check_instant_sorcery_cast_triggers()` check function
- [ ] Wire into the engine cast resolution path (type-filtered variant of generic spell-cast triggers)
- [ ] Integration tests verifying only instant/sorcery casts fire, not creature/artifact/enchantment casts
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M
