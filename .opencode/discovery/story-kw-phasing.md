# Story: Phasing (CR 702.26)

## User Story
As an MTG engine developer, I want a new phasing keyword module with real apply() and integration tests, so that cards with phasing work correctly in the engine.

## Context
No file exists for phasing. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.26**: "Phasing is a static ability that modifies the rules of the untap step. 'Phasing' means 'This permanent phases in or out before you untap during each of your untap steps.' While phased out, it's treated as though it doesn't exist."
- **CR 702.26e**: "Phased-out permanents are treated as though they don't exist. They can't be affected by spells, abilities, or anything else."
- **Example card**: Reality Ripple — "Phasing (This phases in or out before you untap during each of your untap steps. While phased out, it's treated as though it doesn't exist.)"
- **Rule source**: Cyclical phasing in/out during untap step

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/phasing.py` with `Phasing` class extending `PassiveKeyword`
- [ ] `check_phasing(game_state, permanent_id) -> bool` detects if a permanent has phasing
- [ ] `handle_phasing(game_state, player_name) -> GameState` called during untap step, before untapping
- [ ] Phasing alternates: a phased-out permanent phases in, a phased-in permanent phases out
- [ ] `phased_out: bool` field added to `Permanent` model
- [ ] Phased-out permanents are excluded from all game events and queries (can't be targeted, don't trigger, etc.)
- [ ] Auras, Equipment, Fortifications attached to a phasing permanent phase out/in with it
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: phasing in/out on untap step, phased out permanent can't be targeted, phased out permanent doesn't trigger, attached Auras phase with permanent, phasing on creatures with summoning sickness, continuous effects while phased out
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: L

## Notes
- Phasing is one of the oldest and most complex keyword abilities
- Phasing happens BEFORE untapping in the untap step (not after)
- Phased-out permanents still "remember" their state (tapped/untapped, counters, etc.)
- Auras/Equipment attached to a phasing permanent phase with it
- If a token phases out, it ceases to exist (SBA) — actually, no, phased out tokens exist but can't be interacted with
- Actually CR 702.26f: "If a token phases out, it ceases to exist." — yes tokens cease to exist when phasing out
- Requires extensive engine changes to the zone/visibility system
