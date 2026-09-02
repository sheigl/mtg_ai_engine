# Story: Planar Dice Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a planar dice trigger pattern so that Planechase cards with planar dice roll triggers fire correctly.

## Comprehensive Rules Grounding
- **CR 702.XX**: "Planechase uses a planar die. When a player rolls the planar die, the result determines whether the current plane changes or a chaos ability triggers."
- **Example card**: "Whenever you roll the planar die, you may return target card from your graveyard to your hand."

## Acceptance Criteria
- [ ] Add `PLANAR_DICE_TRIGGER_PATTERNS` regex patterns for "whenever you roll the planar die" and "whenever a player rolls the planar die"
- [ ] Add `check_planar_dice_triggers()` check function
- [ ] Wire into the engine planar die roll resolution path
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M
