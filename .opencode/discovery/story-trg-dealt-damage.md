# Story: Dealt Damage / Receives Damage Trigger (CR 119.3)

## User Story
As an MTG engine developer, I want a "is dealt damage" trigger pattern with check function and engine wiring, so that cards with "whenever ~ is dealt damage" triggered abilities fire correctly, distinct from "deals damage" triggers.

## Context
The existing `DAMAGE_TRIGGER_PATTERNS` and `check_damage_triggers()` capture "whenever ~ deals damage" (from the source side). However, the receiver side — "whenever ~ is dealt damage" — has no dedicated pattern. Cards like [[Stuffy Doll]] and [[Ill-Tempered Loner]] trigger when they receive damage.

### Comprehensive Rules Grounding
- **CR 119.3**: "Whenever damage is dealt, the damaged permanent or player loses that much life."
- **Game event**: Damage is assigned to a permanent or player by a damage source
- **Example card**: *Stuffy Doll* — "Whenever ~ is dealt damage, it deals that much damage to target permanent or player."

## Acceptance Criteria
- [ ] Create `DEALT_DAMAGE_TRIGGER_PATTERNS` list with regexes matching: "whenever (?:this|~) is dealt damage", "whenever (?:a|an) (.*?) is dealt damage", "whenever (?:this|~) would be dealt damage"
- [ ] Create `check_dealt_damage_triggers(game_state, damaged_perm_ids: list[str])` that queues PendingTriggers
- [ ] Wire into damage resolution path in stack.py's `_deal_damage()` and combat/core.py's `assign_combat_damage()` for the receiving side
- [ ] Integration tests: creature receives combat damage fires trigger, creature deals damage does NOT fire (use existing deals-damage trigger), self-referential guard
- [ ] No regressions

## Dependencies
- None (new complementary trigger pattern)

## Priority: Medium

## Estimated Effort: M

## Notes
- This is the receiver-side of damage — distinct from the existing source-side damage trigger
- "Would be dealt damage" is a separate variant for replacement effects
- Forge's trigger: `DealtDamageTrigger` (receiver) vs `DealsDamageTrigger` (source)
