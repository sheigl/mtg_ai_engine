# Story: Equip Timing / Sorcery Speed (CR 702.6)

## User Story
As a game engine developer, I want equip to be restricted to sorcery speed (main phase, priority, empty stack), so that the equip timing restriction is enforced per CR 702.6a.

## Context
Equip is an activated ability with a sorcery-speed timing restriction. The player can only activate equip during their own main phase, when the stack is empty, and when they have priority. This is the same timing restriction as casting a sorcery. The sorcery-speed restriction applies to EQUIP specifically (the keyword ability), not to all activated abilities — some abilities can be activated at instant speed.

### Comprehensive Rules Grounding
- **CR 702.6a**: "Equip is an activated ability of Equipment cards. 'Equip [cost]' means '{cost}: Attach this permanent to target creature you control. Activate this ability only any time you could cast a sorcery.'"
- **CR 702.6b**: "An equipment's equip ability can't be activated if the equipment is already attached to a creature."
- **CR 307.1**: "A sorcery can be cast only during the controller's main phase, when the stack is empty."
- **Example card**: Sword of Fire and Ice — "Equip {2}"

## Acceptance Criteria
- [ ] Equip activation is gated to: controller's main phase, stack is empty, controller has priority
- [ ] `can_activate_equip(gs, equipment_perm, player_name) -> bool` validates timing
- [ ] Equip is blocked during combat phase, end step, opponent's turn, or when stack is not empty
- [ ] Equip cost is paid from mana pool (as part of activation)
- [ ] Equip targets a creature you control (must be a legal target when activated)
- [ ] Equipment already attached to a creature: equip can't be activated (CR 702.6b)
- [ ] Legal actions system includes equip when conditions are met
- [ ] Integration tests cover: equip during main phase (allowed), equip during combat (blocked), equip with stack (blocked), equip on opponent's turn (blocked), equip already attached (blocked), equip targeting legality
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- This is a rule-level companion to `story-kw-equip.md` — focuses on the timing restriction, not attachment mechanics
- Story: Targeting Rules (CR 115, 601.2c) — equip targeting validation

## Priority: Low

## Status: ❌ Not Implemented

### Gap Description
equip.py exists with Equip keyword class (detection, cost parsing) but its apply() method is a no-op (returns game_state unchanged). There is no can_activate_equip() function, no sorcery-speed timing validation for equip activation, no equip action in legal actions, and no equip cost payment pipeline. Equip is detected but never actually usable in game.

## Estimated Effort: S

## Notes
- The sorcery-speed restriction is the most commonly misunderstood aspect of equip
- "Activate only as a sorcery" means the same timing as casting a sorcery spell
- Equip's timing is not inherent to the ability type (activated ability) but is explicitly stated in the rules for equip
- All equip abilities have this restriction unless explicitly modified by another effect
- The engine should have a general `validate_sorcery_timing(gs, player) -> bool` helper that equip (and other sorcery-speed abilities) can reuse
