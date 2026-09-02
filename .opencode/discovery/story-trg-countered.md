# Story: Countered Trigger (CR 701.5)

## User Story
As an MTG engine developer, I want a "countered" trigger pattern with check function and engine wiring, so that cards with "whenever a spell is countered" triggered abilities fire correctly.

## Context
No countered trigger pattern exists in triggers.py. When a spell on the stack is countered (via a counterspell effect), it moves from the stack to its owner's graveyard. Cards like [[Spellstutter Sprite]] and [[Torrent of Souls]] have abilities that trigger when spells are countered.

### Comprehensive Rules Grounding
- **CR 701.5**: "To counter a spell or ability means to remove it from the stack. It's put into its owner's graveyard."
- **Game event**: A spell or ability is removed from the stack by a counter effect
- **Example card**: *Torrent of Souls* — "When ~ is countered, you may return target card from your graveyard to your hand."

## Acceptance Criteria
- [ ] Create `COUNTERED_TRIGGER_PATTERNS` list with regexes matching: "whenever (?:a|an) spell is countered", "whenever (?:this|~) is countered", "whenever a spell you control is countered"
- [ ] Create `check_countered_triggers(game_state, countered_stack_obj)` that iterates battlefield permanents and queues PendingTriggers
- [ ] Wire into stack.py's counter resolution BEFORE removing the countered spell from the stack
- [ ] Integration tests: countered spell fires trigger, non-counter removal does NOT fire, self-referential guard
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: High

## Estimated Effort: M

## Notes
- **Timing is critical**: The countered event must fire BEFORE the spell is removed from the stack so self-referential triggers can still access the card data
- Forge's trigger: `CounteredTrigger`
- Already identified as P0 in SPRINT7-P0-missing-triggers.md
