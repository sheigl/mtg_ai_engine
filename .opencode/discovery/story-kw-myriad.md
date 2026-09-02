# Story: Myriad (CR 702.117)

## User Story
As an MTG engine developer, I want a new myriad keyword module with real apply() and integration tests, so that cards with myriad work correctly in the engine.

## Context
No file exists for myriad. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.117**: "Myriad is a triggered ability. 'Myriad' means 'Whenever this creature attacks, for each opponent other than the defending player, you may create a token that's a copy of this creature that's tapped and attacking that opponent or a planeswalker they control. Exile the tokens at the end of combat.'"
- **Example card**: Blade of Selves — "Myriad (Whenever this creature attacks, for each opponent other than the defending player, you may create a token that's a copy of this creature that's tapped and attacking that opponent or a planeswalker they control. Exile the tokens at the end of combat.)"
- **Rule source**: Attack-triggered token copy creation

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/myriad.py` with `Myriad` class extending `TriggeredKeyword`
- [ ] `check_myriad_trigger(game_state, attacker_id) -> bool` detects myriad on attacking creature
- [ ] `apply_myriad(game_state, attacker_id) -> GameState` creates token copies tapped and attacking each other opponent
- [ ] Token copies must be exiled at end of combat (delayed trigger)
- [ ] Tokens enter as exact copies of the original creature (including counters, attachments, etc.)
- [ ] For multiplayer: creates a token for each opponent other than the defending player
- [ ] For duel (2-player): no tokens created (no other opponents)
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: basic myriad in 2-player (no tokens), myriad in 3+ player, token copy properties match, tokens are tapped and attacking, exile at end of combat, token-specific rules (no soulbond, etc.)
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- In a 2-player duel, myriad does nothing (no other opponents to create tokens attacking)
- Tokens must be copies including all modifications (counters, enchantments, equipment)
- The delayed exile trigger at end of combat is mandatory
- Primarily from Commander-focused sets
- Needs careful multiplayer opponent detection
