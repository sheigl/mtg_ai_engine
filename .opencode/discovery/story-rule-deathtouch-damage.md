# Story: Deathtouch Damage Rules (CR 702.2)

## User Story
As a game engine developer, I want deathtouch damage to make any nonzero damage amount lethal for damage assignment purposes, so that deathtouch correctly interacts with trample and combat damage assignment per CR 702.2.

## Context
Deathtouch makes any nonzero damage amount lethal. This primarily affects two scenarios: (1) A creature with deathtouch that deals combat damage to another creature destroys it (via SBA) because any nonzero damage is considered lethal. (2) A creature with deathtouch AND trample only needs to assign 1 damage to each blocker for lethal damage (CR 702.2b), allowing the rest of its power to trample over to the defending player.

### Comprehensive Rules Grounding
- **CR 702.2b**: "Any nonzero amount of combat damage assigned to a creature by a source with deathtouch is considered to be lethal damage, regardless of that creature's toughness."
- **CR 702.2c**: "Damage from a source with deathtouch is considered to be lethal damage for the purpose of determining what damage can be assigned to the defending player."
- **Example card**: Wurmcoil Engine — "Deathtouch, lifelink" — assigns 1 damage per blocker (lethal), rest tramples over
- **CR 704.5h**: "If a creature has toughness greater than 0 and has been dealt lethal damage, it's destroyed."

## Acceptance Criteria
- [x] `is_lethal(damage_amount, source_has_deathtouch)` returns True if damage > 0 and source has deathtouch
- [x] `min_lethal_damage(source_has_deathtouch)` returns 1 if deathtouch (vs normally full toughness)
- [x] Combat damage assignment: deathtouch allows 1 damage per blocker to be lethal
- [x] Trample + deathtouch: only 1 damage needs to be assigned to each blocker; excess tramples
- [x] Non-combat damage: deathtouch also makes any damage from that source lethal to creatures
- [x] Deathtouch does NOT affect damage to players or planeswalkers (only creatures)
- [x] SBA: creature with lethal deathtouch damage is destroyed
- [x] Integration tests cover: deathtouch lethal damage, deathtouch + trample (1 damage per blocker), non-combat deathtouch, deathtouch to player (no special effect), multiple blockers with deathtouch
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Trample Damage Assignment (CR 702.19) — deathtouch + trample interaction
- Story: State-Based Actions (CR 704) — lethal damage SBA
- Keyword story: `story-kw-deathtouch.md` — the keyword module implementation

## Priority: Medium

## Status: ✅ Complete

## Estimated Effort: M

## Notes
- This story covers the RULES ASPECTS of deathtouch damage (CR 702.2b/c), while `story-kw-deathtouch.md` covers the keyword module implementation
- The deathtouch + trample interaction is one of the most common rules questions in Magic
- Deathtouch is already implemented in the engine (P0 Combat Modifiers refactoring completed 2026-07-17)
- Key existing functions: `has_deathtouch()`, `is_lethal()`, `min_lethal_damage()`, `apply_deathtouch_damage()`
- Deathtouch does NOT stack — two deathtouch sources still need only 1 damage per blocker for lethal
- Deathtouch works with any damage, not just combat damage — a card that says "deal 1 damage to target creature" kills it if the source has deathtouch
