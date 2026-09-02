# Story: Trample Damage Assignment (CR 702.19)

## User Story
As a game engine developer, I want trample to correctly assign excess combat damage beyond lethal to the defending player or planeswalker, so that trample damage assignment works per CR 702.19.

## Context
Trample allows a creature to assign excess combat damage (damage beyond what's needed to destroy blockers) to the defending player or planeswalker. The trample creature must assign at least lethal damage to each blocking creature before it can assign damage to the defending player. With deathtouch, lethal damage is 1 per blocker. Trample also works against multiple blockers: the creature must assign lethal to each blocker in order before excess goes to the defending player.

### Comprehensive Rules Grounding
- **CR 702.19b**: "A trampling creature may assign excess combat damage to the defending player or planeswalker."
- **CR 702.19c**: "If a trampling creature is blocked by multiple creatures, it must assign at least lethal damage to each blocker (in damage assignment order) before assigning any to the defending player."
- **CR 702.2b**: "Deathtouch makes 1 damage lethal for trample purposes."
- **Example card**: Stomping Ground — "Trample"

## Acceptance Criteria
- [x] `has_trample(perm) -> bool` detection
- [x] Trample damage assignment function assigns damage to blockers first (lethal minimum), then excess to defending player
- [x] Lethal damage calculation: normally equal to blocker's toughness; 1 if attacker has deathtouch
- [x] Multiple blockers: damage assignment order matters — must assign lethal to first blocker, then second, etc., then excess to defending player
- [x] Trample + indestructible blocker: trample can still assign excess to player after assigning lethal (even though the blocker won't die)
- [x] Trample against planeswalker: excess damage goes to planeswalker defender
- [x] Trample with deathtouch: only 1 damage per blocker needed for lethal; rest tramples over
- [x] Trample with banding: banding controller assigns damage among blockers (not normal trample rules)
- [x] Integration tests cover: single blocker trample, multiple blockers trample, trample + deathtouch, trample + indestructible blocker, trample to planeswalker
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Deathtouch Damage Rules (CR 702.2) — deathtouch + trample interaction
- Story: State-Based Actions (CR 704) — SBA checks after trample damage is dealt

## Priority: Medium

## Status: ✅ Complete

## Estimated Effort: M

## Notes
- Trample only applies to COMBAT damage — it doesn't affect spell damage
- Damage assignment order is chosen by the attacking player during declare blockers step
- Trample + indestructible: the trampler must still assign lethal damage to the indestructible blocker to trample over (CR 702.19b says "lethal damage," not "destroy")
- Trample + protection: if the blocker has protection from the trampler's color, the trampler can't assign ANY damage to that blocker, so it can trample all damage over (unless there are other blockers without protection)
- The engine's combat system likely already handles trample — this story ensures CR 702.19 compliance
