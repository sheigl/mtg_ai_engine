# Story: Token Created (General) Trigger (CR 110.5)

## User Story
As an MTG engine developer, I want a general token-created trigger pattern so that cards with "whenever a token is created" (general, not "one or more") abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 110.5**: "A token is a marker used to represent any permanent that isn't represented by a card."
- **Example card**: Anointed Procession — "If an effect would create one or more tokens under your control, it creates twice that many instead." (Replacement effect that cares about token creation)

## Acceptance Criteria
- [ ] Add `TOKEN_CREATED_GEN_TRIGGER_PATTERNS` regex patterns for "whenever a token is created" and "whenever you create a token"
- [ ] Add `check_token_created_gen_triggers()` check function (general variant, distinct from existing check_token_triggers "one or more" variant)
- [ ] Wire into the engine token creation path
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M
