# Story: Collect Evidence Trigger (CR 701.XX)

## User Story
As an MTG engine developer, I want a collect-evidence trigger pattern with check function and engine wiring, so that cards with "Whenever you collect evidence" triggered abilities from Murders at Karlov Manor fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Collect evidence" is a keyword mechanic from Murders at Karlov Manor (MKM) where players exile cards from their graveyard with total mana value meeting or exceeding a threshold.

### Comprehensive Rules Grounding
- **CR 701.XX**: "To collect evidence N, exile any number of cards from your graveyard with total mana value N or greater. Some abilities trigger 'whenever you collect evidence.'"
- **Example card**: *Cunning Coyote* — "Whenever you collect evidence, Cunning Coyote gets +2/+2 until end of turn."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into evidence collection resolution flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Collect evidence is a cost that exiles cards from the graveyard with sufficient total mana value.
- The trigger fires when the cost is paid (when evidence is collected), not when the effect resolves.
- Example cards: *Cunning Coyote*, *Dramatic Accusation*, *Unscrupulous Agent*, *Rubblebelt Maverick*.
