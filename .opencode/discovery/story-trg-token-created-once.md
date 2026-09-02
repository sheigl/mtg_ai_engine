# Story: Token Created "One or More" Trigger (CR 110.5)

## User Story
As an MTG engine developer, I want a "one or more tokens enter" trigger pattern with check function and engine wiring, so that cards with "whenever one or more tokens enter under your control" triggered abilities fire correctly, grouped per event rather than per-token.

## Context
The existing `TOKEN_TRIGGER_PATTERNS` and `check_token_triggers()` handle per-token creation events. However, the "one or more" variant (CR 110.5) fires once per token-creation event regardless of how many tokens are created simultaneously. Cards like [[Anointed Procession]] double tokens and need the trigger to fire only once even when creating multiple tokens.

### Comprehensive Rules Grounding
- **CR 110.5**: "A token is a marker used to represent any permanent on the battlefield that isn't represented by a card."
- **Game event**: One or more tokens enter the battlefield as part of a single resolution
- **Example card**: *Anointed Procession* — "If an effect would create one or more tokens under your control, it creates twice that many of those tokens instead."

## Acceptance Criteria
- [ ] Create `TOKEN_CREATED_ONCE_TRIGGER_PATTERNS` list with regexes matching: "whenever one or more tokens", "whenever a token enters"
- [ ] Create `check_token_created_on_once_triggers(game_state, controller: str, token_ids: list[str])` that fires once per creation event
- [ ] Wire into token creation path in stack.py, grouping simultaneous tokens into one trigger
- [ ] Integration tests: creating 3 tokens from one effect fires trigger once, creating 1 token fires once, non-token ETB does NOT fire
- [ ] No regressions

## Dependencies
- None (new complementary trigger pattern)

## Priority: High

## Estimated Effort: S

## Notes
- The distinction is "per event" vs "per token" — this is a grouped variant of the existing token trigger
- Forge's trigger: `TokenCreatedTrigger` (grouped by default)
