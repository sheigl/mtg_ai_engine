# Story: Phase In/Out Trigger (CR 702.26)

## User Story
As an MTG engine developer, I want a "phases in/phases out" trigger pattern with check function and engine wiring, so that cards with "whenever ~ phases in" triggered abilities fire correctly.

## Context
No phasing trigger pattern exists in triggers.py. Phasing (CR 702.26) is an old keyword that causes permanents to phase out during their controller's untap step and phase in during their controller's untap step. Several cards have triggers when they phase in or out.

### Comprehensive Rules Grounding
- **CR 702.26b**: "During a player's untap step, the player turns face down all permanents they control that phase in that turn."
- **CR 702.26c**: "Phasing doesn't leave the battlefield. A permanent that phases out is not on the battlefield."
- **Game event**: A permanent phases in (returns to battlefield) or phases out (leaves battlefield)
- **Example card**: *Teferi's Isle* — "Phasing. Whenever ~ phases in or phases out, draw a card."

## Acceptance Criteria
- [ ] Create `PHASE_TRIGGER_PATTERNS` list with regexes matching: "whenever (?:this|~) phases in", "whenever (?:this|~) phases out", "whenever (?:a|an) (.*?) phases in/out"
- [ ] Create `check_phase_in_triggers()` and `check_phase_out_triggers()` that queue PendingTriggers
- [ ] Wire into the phasing handler in turn_manager.py's untap step
- [ ] Integration tests: phasing in fires trigger, phasing out fires separate trigger
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: Low

## Estimated Effort: M

## Notes
- Phase in and phase out are distinct events — consider separate check functions
- Phasing does NOT trigger ETB/LTB effects per CR 702.26e
- Forge's trigger: `PhasedInTrigger`, `PhasedOutTrigger`
