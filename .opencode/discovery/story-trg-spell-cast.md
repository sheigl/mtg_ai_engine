# Story: Spell Cast / Ability Activated Trigger (CR 601.2)

## User Story
As an MTG engine developer, I want a generic spell-cast / ability-activated trigger pattern so that cards with "whenever you cast a spell" or "whenever you activate an ability" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 601.2**: "To cast a spell is to take it from where it is (usually the hand), put it on the stack, and pay its costs."
- **Example card**: "Whenever you cast an instant or sorcery spell, draw a card." (e.g., Guttersnipe)

## Acceptance Criteria
- [ ] Add `SPELL_CAST_TRIGGER_PATTERNS` regex patterns for "whenever you cast a spell", "whenever you cast a [type] spell", and "whenever you activate an ability"
- [ ] Add `check_spell_cast_triggers()` check function
- [ ] Wire into the engine cast resolution path
- [ ] Integration tests with various card types (instant, sorcery, creature, artifact, enchantment)
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M
