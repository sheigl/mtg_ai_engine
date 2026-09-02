# Story: Exert (CR 701.26)

## User Story
As a game engine developer, I want the exert mechanic to function correctly per the Comprehensive Rules, so that players can choose to exert creatures during attacks, causing them to not untap during the next untap step.

## Context
Exert is a choice made as a creature is declared as an attacker. The creature gains an additional effect (typically a bonus) but does not untap during its controller's next untap step. The "doesn't untap" effect can stack if a creature is exerted multiple turns in a row.

### Comprehensive Rules Grounding
- **CR 701.26a**: "To exert a permanent, choose to untap it during your next untap step rather than tapping it now. (An exerted permanent won't untap during your next untap step.)"
- **CR 701.26b**: "A permanent can be exerted even if it's already tapped."
- **CR 701.26c**: "If a permanent is exerted multiple times before your next untap step, each instance of exert adds another 'doesn't untap' effect. They all wear off at the same time."
- **Example card**: Glorybringer — "You may exert Glorybringer as it attacks. When you do, it deals 4 damage to target non-Dragon creature."
- **Example card**: Ahn-Crop Crasher — "You may exert Ahn-Crop Crasher as it attacks. When you do, target creature can't block this turn."

## Acceptance Criteria
- [ ] `exert(gs, perm_id, player_name)` marks the permanent as exerted
- [ ] Exert is declared as the creature is declared as an attacker (during declare attackers step)
- [ ] Exerted permanent does NOT untap during controller's next untap step
- [ ] Exert tracking: `exerted_until` field stores until which turn/step the effect lasts
- [ ] Multiple exerts stack: exerted N times means N instances of "doesn't untap" (all expire together)
- [ ] Exert effect wears off after the controller's next untap step (functionally the creature just doesn't untap that one time)
- [ ] Exert can be chosen even if the creature is already tapped (CR 701.26b)
- [ ] The exert choice is part of the attack declaration — the creature's "you may exert" ability is optional
- [ ] The exert trigger (bonus effect) fires when the creature is exerted
- [ ] Integration test: exert Glorybringer, verify bonus damage trigger and creature doesn't untap next turn
- [ ] Integration test: exert an already-tapped creature
- [ ] Integration test: double exert — creature misses two untap steps (or one with stacked effect)
- [ ] Full regression suite passes

## Dependencies
- Declare Attackers Step (story-turn-declare-attackers.md)
- Untap Step (story-turn-untap-step.md)
- Trigger system (exert triggers)

## Priority: High
## Status: ❌ Not Implemented

> **Gap**: No `exert()` function, no `exerted_until` field on Permanent model, no exert keyword implementation anywhere in the engine.

## Estimated Effort: M
