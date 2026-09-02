# Story: Split Second (CR 702.61)

## User Story
As a game engine developer, I want split second to function correctly per the Comprehensive Rules, so that spells with split second can only be responded to by triggered abilities and mana abilities, not by other spells or activated abilities.

## Context
This game action is already documented under the rule story `story-rule-split-second.md`. This file serves as an action-oriented reference.

### Comprehensive Rules Grounding
- **CR 702.61a**: "Split second is a keyword ability that prevents players from casting spells or activating abilities while the spell with split second is on the stack."
- **CR 702.61b**: "Players may still activate mana abilities and trigger abilities will still trigger."
- **CR 702.61c**: "Split second doesn't stop triggered abilities from being put onto the stack."
- **Example card**: Krosan Grip — "Split second. Destroy target artifact or enchantment."

## Acceptance Criteria
- [x] See `story-rule-split-second.md` for full acceptance criteria
- [x] While spell with split second is on stack, no other spells can be cast
- [x] While spell with split second is on stack, no activated abilities (except mana abilities) can be activated
- [x] Triggered abilities still trigger and are put onto the stack

## Dependencies
- story-rule-split-second.md (full rules story)
- Priority System (story-turn-priority-system.md)

## Priority: Medium
## Status: ✅ Complete

## Estimated Effort: M
