# Story: Attacker Becomes Unblocked Trigger (CR 509.1)

## User Story
As an MTG engine developer, I want an "attacker becomes unblocked" trigger pattern with check function and engine wiring, so that cards with "whenever ~ becomes unblocked" triggered abilities fire correctly.

## Context
No "attacker becomes unblocked" trigger pattern exists in triggers.py. When an attacking creature has no blockers assigned, it becomes unblocked. Some creatures have triggered abilities that fire when they're unblocked (e.g., [[Slith Firewalker]]). This is distinct from "becomes blocked" (has blockers) and "is unblocked" (state).

### Comprehensive Rules Grounding
- **CR 509.1**: "The defending player chooses which of their creatures, if any, will block. A creature that isn't blocked is called an unblocked creature."
- **Game event**: An attacking creature has no blockers assigned during declare blockers step
- **Example card**: *Slith Firewalker* — "Whenever ~ becomes unblocked, put a +1/+1 counter on it."

## Acceptance Criteria
- [ ] Create `ATTACKER_UNBLOCKED_TRIGGER_PATTERNS` list with regexes matching: "whenever (?:this|~) becomes unblocked", "whenever (?:a|an) (.*?) becomes unblocked"
- [ ] Create `check_attacker_unblocked_triggers(game_state, attacker_id: str)` that queues PendingTriggers
- [ ] Wire into combat/core.py's declare blockers or combat damage step for unblocked attackers
- [ ] Integration tests: unblocked attacker fires trigger, blocked attacker does NOT fire, creature with menace that can't be blocked fires
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: Medium

## Estimated Effort: M

## Notes
- An attacker becomes unblocked if no blockers are assigned to it
- Also applies when all blockers are removed before combat damage (e.g., via "remove from combat" effects)
- Forge's trigger: `AttackerUnblockedTrigger`
