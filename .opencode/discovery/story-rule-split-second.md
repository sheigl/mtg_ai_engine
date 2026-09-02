# Story: Split Second (CR 702.61)

## User Story
As a game engine developer, I want spells with split second to prevent players from casting spells or activating non-mana abilities while the spell is on the stack, so that split second's "uncounterable" protection works per CR 702.61.

## Context
Split second is a keyword ability that prevents players from casting spells or activating abilities (except mana abilities) while a spell with split second is on the stack. This effectively means the spell can't be responded to by most spells or abilities. However, triggered abilities still work (they don't require a player to "cast" or "activate"), and mana abilities can still be activated.

### Comprehensive Rules Grounding
- **CR 702.61a**: "Split second means as long as this spell is on the stack, players can't cast other spells or activate abilities that aren't mana abilities."
- **CR 702.61b**: "Triggered abilities still trigger and resolve normally even while a split second spell is on the stack."
- **CR 605.1**: "Mana abilities are abilities that produce mana and don't target."
- **Example card**: Krosan Grip — "Split second (As long as this spell is on the stack, players can't cast spells or activate abilities that aren't mana abilities.)"

## Acceptance Criteria
- [x] `has_split_second(spell/card) -> bool` detection
- [x] When a spell with split second is on the stack: no player can cast new spells
- [x] When a split second spell is on the stack: no player can activate non-mana abilities
- [x] Mana abilities CAN still be activated (they don't target and produce mana)
- [x] Triggered abilities STILL trigger and go on the stack normally
- [x] Special actions (playing a land, paying morph costs) can still be taken
- [x] When the split second spell leaves the stack (resolves, countered, exiled), normal play resumes
- [x] The split second spell itself CAN still be countered — split second doesn't grant "can't be countered" by itself (it just prevents new counterspells from being cast)
- [x] Integration tests cover: split second prevents spell casting, split second prevents ability activation, mana abilities still work, triggered abilities still work, split second doesn't prevent uncounterability
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone modifier for stack behavior)

## Priority: Medium

## Status: ✅ Complete

## Estimated Effort: M

## Notes
- Split second is a powerful protection ability — it effectively makes the spell unrespondable (but not uncounterable by already-existing effects)
- Key nuance: if a "counter target spell" trigger is already on the stack when the split second spell is cast, the trigger can still counter it
- Split second does NOT stop special actions: playing a land, suspending a card, turning a face-down creature face-up (if it has morph)
- Split second was introduced in Time Spiral block and used in a few subsequent sets
- "Mana abilities" are abilities that: (1) produce mana, (2) don't target, and (3) aren't loyalty abilities (unless they produce mana AND are loyalty abilities, which is a special case)
- The engine's stack/priority system needs a `split_second_active` flag that gates spell casting and ability activation
