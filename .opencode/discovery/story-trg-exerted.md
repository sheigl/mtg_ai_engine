# Story: Exerted Trigger (CR 701.26)

## User Story
As an MTG engine developer, I want an "exerted" trigger pattern with check function and engine wiring, so that cards with "whenever ~ becomes exerted" triggered abilities fire correctly.

## Context
No exert trigger pattern exists in triggers.py. The exert mechanic (CR 701.26) was introduced in Amonkhet block. When a creature is exerted, it doesn't untap during its controller's next untap step, and some creatures have "whenever ~ becomes exerted" triggers.

### Comprehensive Rules Grounding
- **CR 701.26**: "To exert a permanent, an effect marks it as being exerted. An exerted permanent doesn't untap during its controller's next untap step."
- **Game event**: A creature is marked as exerted (usually when it attacks)
- **Example card**: *Glorybringer* — "You may exert ~ as it attacks. When you do, it deals 4 damage to target creature."

## Acceptance Criteria
- [ ] Create `EXERTED_TRIGGER_PATTERNS` list with regexes matching: "when(?:ever)? (?:this|~|this creature) becomes exerted", "whenever you exert"
- [ ] Create `check_exerted_triggers(game_state, exerted_perm_ids: list[str])` that iterates permanents and queues PendingTriggers
- [ ] Wire into the exert action handler (where permanents are marked exerted)
- [ ] Integration tests: exerting a creature fires trigger, non-exerted creature does NOT fire, self-referential guard
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: Medium

## Estimated Effort: M

## Notes
- Exert typically happens as an optional cost during attack declaration
- The exert marker is temporary (lasts until next untap step)
- Forge's trigger: `ExertedTrigger`
