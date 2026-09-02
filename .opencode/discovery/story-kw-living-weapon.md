# Story: Living Weapon (CR 702.70)

## User Story
As an MTG engine developer, I want a new living weapon keyword module with real apply() and integration tests, so that cards with living weapon work correctly in the engine.

## Context
No file exists for living weapon. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.70**: "Living weapon is a triggered ability. 'Living weapon' means 'When this Equipment enters, create a 0/0 black Phyrexian Germ creature token, then attach this Equipment to it.'"
- **Example card**: Batterskull — "Living weapon (When this Equipment enters, create a 0/0 black Phyrexian Germ creature token, then attach this Equipment to it.)"
- **Rule source**: ETB trigger that creates a token and attaches to it

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/living_weapon.py` with `LivingWeapon` class extending `TriggeredKeyword`
- [ ] `check_living_weapon(oracle_text) -> bool` detects living weapon keyword
- [ ] `apply_living_weapon(game_state, equipment_id, controller) -> GameState` creates 0/0 black Phyrexian Germ creature token and attaches equipment
- [ ] The Germ token has no abilities (base 0/0, relies on equipment for stats)
- [ ] Equipment is attached automatically as part of the ETB trigger resolution
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: basic living weapon creates Germ token, equipment attaches to Germ, Germ token is 0/0 black Phyrexian, token vanished if equipment leaves, living weapon on non-equipment (does nothing), multiple living weapons
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- The Germ token's power/toughness comes entirely from the equipment (it's 0/0 base)
- If the equipment is destroyed, the Germ token dies as a state-based action (0/0)
- Mirrodin Besieged / New Phyrexia mechanic
- Appears on several iconic equipment cards (Batterskull, Kaldra Compleat)
- Token is black Phyrexian Germ creature (not artifact)
