# Story: Entwine (CR 702.41)

## User Story
As an MTG engine developer, I want the Entwine keyword module to have a real `apply()` implementation with integration tests, so that modal spells with Entwine can be cast with all modes chosen when the additional cost is paid.

## Context
The Entwine keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.41a**: "Entwine is an additional cost for modal spells. 'Entwine {cost}' means 'You may pay an additional {cost}. If you do, you choose all modes instead of just one.'"
- **Rule source**: Additional cost modifier that expands mode selection on modal spells
- **Example card**: Tooth and Nail — "Entwine {2}" (pay {2} additional on cast, choose both modes: tutor creature to hand AND put creature onto battlefield)

## Acceptance Criteria
- [ ] `EntwineKeyword.apply(game_state, permanent)` implements full entwine logic: detects entwine cost; queues `pending_entwine_choice` for human players
- [ ] AI auto-resolves by paying if mana affordable (heuristic: pay if extra mana available after base cost)
- [ ] Entwine is an additional cost — if paid, player selects all modes of the spell instead of just one
- [ ] `modes_chosen` on StackObject updated to include all modes when entwine is paid
- [ ] Integration tests in `tests/engine/test_entwine_integration.py` with 8-15 tests
- [ ] Full regression suite passes (2792+ tests, 0 failures)

## Dependencies
- None

## Priority: Medium

## Estimated Effort: S

## Notes
- **Modal spell support**: Entwine only applies to modal spells (spells with "Choose one —" or multiples). The engine's modal choice infrastructure must support selecting all modes. Reference how `modes_chosen: list[int]` on StackObject tracks mode selection.
- **Cost payment**: Follow the Kicker (KW-16) pattern — additional cost queued for human players, auto-resolved for AI based on mana affordability.
- **Entwine vs Kicker**: Both are additional costs but entwine specifically affects mode selection while kicker adds a spell effect. They can coexist on the same spell.
