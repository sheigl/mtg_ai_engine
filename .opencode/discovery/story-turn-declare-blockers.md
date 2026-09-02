# Story: Declare Blockers Step (CR 509)

## User Story
As a game engine developer, I want the declare blockers step to function correctly per CR 509, so that the defending player chooses which creatures block which attackers.

## Context
The declare blockers step is the third step of the combat phase (after declare attackers). The defending player chooses which creatures block which attackers. Each creature can block only one attacker (unless it has banding or a special ability). An attacker can be blocked by multiple creatures if it has menace (requires at least 2 blockers). The current engine has blocking logic in `combat/core.py`. After blockers are declared, priority is granted and players may cast instants before damage.

### Comprehensive Rules Grounding
- **CR 509.1**: "The defending player declares blockers. They choose which creatures they control, if any, will block. They choose which attacking creature each blocking creature blocks."
- **CR 509.2**: "Each creature can block only one attacking creature each combat."
- **CR 509.3**: "An attacking creature that's blocked by multiple creatures is blocked by all of them."
- **CR 509.4**: "The defending player arranges the blocking creatures' order for each attacking creature."
- **CR 702.111b**: "A creature with menace can't be blocked except by two or more creatures."
- **Purpose**: Defending player assigns blockers to protect themselves/planeswalkers

## Acceptance Criteria
- [x] Defending player selects which creatures block each attacker
- [x] Each blocker blocks exactly one attacker
- [x] Menace creatures require at least two blockers to be blocked
- [x] Creatures with summoning sickness CAN block (blocking doesn't use tap)
- [x] Player may choose not to block (0 blockers)
- [x] Block assignment order is determined for multi-block situations
- [x] "Can block an additional creature" effects (e.g., Hundred-Handed One) are respected
- [x] "Can't block" restrictions are enforced
- [x] Priority is granted after blockers are declared
- [x] Full regression passes

## Dependencies
- story-turn-declare-attackers.md (Declare Attackers Step)

## Status: ✅ Complete

Implemented: `declare_blockers()` at `combat/core.py:282-396`. Validates blockers (flying/reach, shadow, menace, protection). Handles flanking -1/-1 penalty. `order_blockers()` at line 399 for damage assignment ordering. Legal actions at `game.py:3340-3425`.

## Priority: High
