# Story: Untaps / Becomes Untapped Trigger (CR 302.6)

## User Story
As an MTG engine developer, I want an "becomes untapped" trigger pattern with check function and engine wiring, so that cards with "whenever ~ becomes untapped" triggered abilities fire correctly.

## Context
No "becomes untapped" trigger pattern exists in triggers.py. Several cards have triggered abilities that fire when a permanent untaps — during its controller's untap step or via other effects. This is the complement of the "becomes tapped" trigger.

### Comprehensive Rules Grounding
- **CR 302.6**: "A creature's activated ability with the tap symbol or the untap symbol in its activation cost can't be activated unless the creature has been under its controller's control continuously since the beginning of the most recent turn."
- **Game event**: A permanent's state changes from tapped to untapped
- **Example card**: *Argothian Elder* — "Whenever ~ becomes untapped, add {G}{G}."

## Acceptance Criteria
- [ ] Create `UNTAP_TRIGGER_PATTERNS` list with regexes matching: "whenever (?:this|~) becomes untapped", "whenever (?:a|an) (.*?) becomes untapped", "whenever (?:a|an) (.*?) you control becomes untapped"
- [ ] Create `check_untap_triggers(game_state, untapped_perm_ids: list[str])` that queues PendingTriggers
- [ ] Wire into the untap action handler (where permanents change from tapped to untapped)
- [ ] Integration tests: untapping during untap step fires trigger, tapping does NOT fire, already-untapped stays quiet
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: Medium

## Estimated Effort: M

## Notes
- "Becomes untapped" fires when tapped → untapped state change happens
- Normal untap step untaps all permanents — the trigger fires for each permanent as it untaps
- Forge's trigger: `UntappedTrigger`, `BecomesUntappedTrigger`
