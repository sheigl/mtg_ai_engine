# Story: Attacker Becomes Blocked Trigger (CR 509.1)

## User Story
As an MTG engine developer, I want an "attacker becomes blocked" trigger pattern with check function and engine wiring, so that cards with "whenever ~ becomes blocked" triggered abilities fire correctly, distinct from "whenever ~ blocks" (blocker triggers).

## Context
No "attacker becomes blocked" trigger pattern exists in triggers.py. The existing `BLOCK_TRIGGER_PATTERNS` captures "whenever ~ blocks" (for blocker creatures). But "whenever ~ becomes blocked" is a separate pattern for attackers that have been assigned a blocker.

### Comprehensive Rules Grounding
- **CR 509.1**: "The defending player chooses which of their creatures, if any, will block. A creature that blocks is called a blocker."
- **Game event**: An attacking creature is assigned at least one blocker during declare blockers step
- **Example card**: *Balduvian Warlord* — "Whenever ~ becomes blocked, it deals 1 damage to each creature blocking it."

## Acceptance Criteria
- [ ] Create `ATTACKER_BLOCKED_TRIGGER_PATTERNS` list with regexes matching: "whenever (?:this|~) becomes blocked", "whenever (?:a|an) (.*?) becomes blocked"
- [ ] Create `check_attacker_blocked_triggers(game_state, attacker_id: str, blocker_ids: list[str])` that queues PendingTriggers
- [ ] Wire into combat/core.py's `declare_blockers()` flow after blockers are assigned
- [ ] Integration tests: attacker gets blocker fires trigger, unblocked attacker does NOT fire, blocker's "blocks" and attacker's "becomes blocked" are distinct
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: Medium

## Estimated Effort: M

## Notes
- This is the inverse of the "blocks" trigger — fire on attacker side when blockers are declared
- Pass both the attacker ID and the list of blocker IDs to the check function
- Forge's trigger: `AttackerBlockedTrigger`
