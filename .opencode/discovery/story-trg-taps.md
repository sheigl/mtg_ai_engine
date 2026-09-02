# Story: Taps / Becomes Tapped Trigger (CR 302.6)

## User Story
As an MTG engine developer, I want a "becomes tapped" trigger pattern with check function and engine wiring, so that cards with "whenever ~ becomes tapped" triggered abilities fire correctly.

## Context
No "becomes tapped" trigger pattern exists in triggers.py. Many cards trigger when a permanent becomes tapped — either for mana, as an attack cost, or via an activation. This is distinct from just "tapped" state and fires specifically when the state changes from untapped to tapped.

### Comprehensive Rules Grounding
- **CR 302.6**: "A creature's activated ability with the tap symbol or the untap symbol in its activation cost can't be activated unless the creature has been under its controller's control continuously since the beginning of the most recent turn."
- **Game event**: A permanent's state changes from untapped to tapped
- **Example card**: *Bioessence Hydra* — "Whenever ~ becomes tapped, draw a card."

## Acceptance Criteria
- [ ] Create `TAP_TRIGGER_PATTERNS` list with regexes matching: "whenever (?:this|~) becomes tapped", "whenever a (.*?) becomes tapped", "whenever (?:a|an) (.*?) you control becomes tapped"
- [ ] Create `check_tap_triggers(game_state, tapped_perm_ids: list[str])` that queues PendingTriggers
- [ ] Wire into the tap action handler (where permanents are changed from untapped to tapped)
- [ ] Integration tests: tapping a creature fires trigger, untapping does NOT fire, already-tapped stays quiet
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: Medium

## Estimated Effort: M

## Notes
- "Becomes tapped" is a state change event — fire when the tapped flag changes from False to True
- Many cards trigger on tap: mana abilities, attack declarations, activated abilities with tap symbol
- Forge's trigger: `TappedTrigger`, `BecomesTappedTrigger`
- Distinguish from "is tapped" (state-based check) vs "becomes tapped" (state change event)
