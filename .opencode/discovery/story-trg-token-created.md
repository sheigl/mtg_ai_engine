# Story: Token Created Trigger (CR 110.5 / CR 110.6)

## User Story
As an MTG engine developer, I want token creation triggers wired into the engine event flow, so that cards with "whenever you create a token" abilities fire correctly instead of silently no-op'ing.

## Context
The `check_token_triggers()` function already exists in triggers.py but is NOT called from anywhere in the engine's event flow. This needs wiring into stack.py's token creation helpers (e.g., `_create_token_with_pt_and_keywords()`) after a token enters the battlefield per CR 110.5/110.6.

### Comprehensive Rules Grounding
- **CR 110.5**: "A token is a marker used to represent any permanent on the battlefield that isn't represented by a card."
- **CR 110.6**: "Tokens follow the rules for permanents. Once a token enters the battlefield, it behaves like any other permanent."
- **Game event**: A token permanent is created on the battlefield via an effect (not a card entering as a permanent from another zone)
- **Example card**: *Chatterfang, Squirrel General* — "Whenever you create a token, create an additional 1/1 green Squirrel token."

## Acceptance Criteria
- [ ] Call `check_token_triggers(gs, player_name)` from stack.py's token creation helpers (`_create_token_with_pt_and_keywords()`, `_create_tokens()`, `_create_token_with_keywords()`, etc.) after the token permanent is on the battlefield
- [ ] Also wire into `_create_token_with_abilities`, `_create_token_with_multiple_abilities*`, and any other token creation path
- [ ] Pass the controller name to the check function
- [ ] Capture return value (`gs = check_token_triggers(gs, player_name)`)
- [ ] Integration test: creating a token fires trigger, a non-token card entering the battlefield does NOT fire, creating multiple tokens fires once per token event

## Dependencies
- None

## Priority: High

## Estimated Effort: S

## Notes
- **Token vs non-token**: Only fire for actual token creation (where `is_token=True`). Cards entering the battlefield normally should NOT fire `check_token_triggers()`. The `is_token` flag on the created permanent distinguishes these cases.
- **Multiple creation paths**: There are ~17 `_create_token_*` variants in stack.py. Consider centralizing via a common helper that all variants route through, then wire the trigger call in one place.
- **Existing tests**: The function is tested in `tests/engine/test_new_trigger_types.py` and `tests/engine/test_triggers_expanded.py` — these should continue passing after wiring.
