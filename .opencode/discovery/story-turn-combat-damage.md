# Story: Combat Damage Step (CR 510)

## User Story
As a game engine developer, I want the combat damage step to function correctly per CR 510, so that attacking and blocking creatures deal their combat damage with proper assignment and all keyword interactions (trample, deathtouch, lifelink, infect) are applied.

## Context
The combat damage step is where the main combat damage resolution occurs. Creatures without first strike or double strike (and double strike creatures in their second swing) deal combat damage. Damage assignment order, trample over-assignment, deathtouch lethal damage rules, lifelink life gain, and infect poison counters are all applied during this step. The current engine calls `assign_combat_damage(game_state, first_strike_only=False)` in `begin_step()` at `turn_manager.py` line 365-375, with SBA check and priority grant following.

### Comprehensive Rules Grounding
- **CR 510.1**: "During the combat damage step, creatures that are attacking and blocking deal combat damage."
- **CR 510.2**: "The active player announces how they will assign each attacking creature's combat damage. The defending player announces how they will assign each blocking creature's combat damage."
- **CR 510.3**: "Damage is assigned in the order determined earlier."
- **CR 702.19b**: "Trample: attacking creature can assign excess damage to defending player/planeswalker."
- **CR 702.2c**: "Deathtouch: any amount of damage is considered lethal damage."
- **CR 702.15b**: "Lifelink: damage dealt by a creature with lifelink causes its controller to gain that much life."
- **CR 702.90b**: "Infect: damage dealt to creatures is dealt as -1/-1 counters; damage dealt to players is dealt as poison counters."
- **Purpose**: Apply combat damage and all combat keyword modifiers

## Acceptance Criteria
- [x] All attacking and blocking creatures without first strike deal combat damage
- [x] Double strike creatures deal their second batch of combat damage
- [x] Damage assignment order is respected for multi-blocked/multi-blocking scenarios
- [x] Trample assigns excess damage to defending player/planeswalker
- [x] Deathtouch makes any non-zero damage count as lethal
- [x] Lifelink grants life equal to damage dealt to the controller
- [x] Infect deals -1/-1 counters to creatures and poison counters to players
- [x] State-based actions are checked after damage resolution (creatures die from damage)
- [x] Priority is granted to active player after damage step
- [x] Full regression passes

## Dependencies
- story-turn-first-strike-damage.md (First Strike Damage Step)
- story-turn-declare-blockers.md (Declare Blockers Step)

## Status: ✅ Complete

Implemented: `Step.COMBAT_DAMAGE` at `turn_manager.py:102`. `assign_combat_damage()` at `combat/core.py:564-735` with trample, deathtouch, infect, lifelink, commander damage, monarch/initiative transfer. SBA check after damage.

## Priority: High
