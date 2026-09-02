# Story: Saddle (CR 702.XX — Outlaws of Thunder Junction)

## User Story
As an MTG engine developer, I want a new saddle keyword module with real apply() and integration tests, so that Mount cards with saddle N work correctly in the engine.

## Context
No file exists for saddle. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.XX**: "Saddle is an activated ability. 'Saddle N' means 'Tap any number of other untapped creatures you control with total power N or greater: This permanent becomes saddled until end of turn. Saddle only as a sorcery.'"
- **Rule source**: Activated ability on Mounts/Vehicles that requires tapping other creatures
- **Example card**: Llanowar Knight — "Saddle 2 (Tap any number of other untapped creatures you control with total power 2 or greater: This Mount becomes saddled until end of turn. Saddle only as a sorcery.)"

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/saddle.py` with `Saddle` class extending `KeywordAbility`
- [ ] `parse_saddle(oracle_text) -> int | None` detects saddle N threshold
- [ ] `apply()` checks if the player can tap creatures with total power >= N (other than this creature)
- [ ] `is_saddled(game_state, permanent_id) -> bool` query helper
- [ ] For human players: queues `pending_saddle_choice` with eligible creature selections
- [ ] For AI players: auto-resolves (taps the minimum number of creatures to meet threshold)
- [ ] Mount becomes "saddled until end of turn" — tracked via `saddled: bool` on Permanent
- [ ] Sorcery speed restriction
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: basic saddle 2, saddle with tapped creatures (can't use), saddle at sorcery speed, saddled until end of turn, mount effects that require saddled, multiple saddles in one turn, creature dies mid-resolution
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Similar to Crew (Vehicles) but with a power threshold and works on Mounts
- The "saddled" status lasts until end of turn (regardless of whether the tapper creatures are still tapped)
- Mounts have abilities that reference "whenever this Mount attacks while saddled, ..."
- Outlaws of Thunder Junction mechanic
- The creature used to saddle cannot be the Mount itself
