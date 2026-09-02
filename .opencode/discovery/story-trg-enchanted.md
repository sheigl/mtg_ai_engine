# Story: Enchanted / Becomes Enchanted Trigger (CR 303.4)

## User Story
As an MTG engine developer, I want a "becomes enchanted" trigger pattern with check function and engine wiring, so that cards with "whenever ~ becomes enchanted" triggered abilities fire correctly.

## Context
No "becomes enchanted" trigger pattern exists in triggers.py. Several creatures have triggered abilities when they become enchanted (when an Aura is attached to them). The existing `ATTACH_TRIGGER_PATTERNS` covers aura attachment from the Aura's perspective, but the enchanted creature's perspective is missing.

### Comprehensive Rules Grounding
- **CR 303.4**: "An Aura spell targets a permanent or player and is put onto the battlefield attached to that permanent or player."
- **Game event**: An Aura becomes attached to a permanent, changing its "enchanted" state
- **Example card**: *Uril, the Miststalker* — "Whenever ~ becomes enchanted, put a +1/+1 counter on it."

## Acceptance Criteria
- [ ] Create `ENCHANTED_TRIGGER_PATTERNS` list with regexes matching: "whenever (?:this|~) becomes enchanted", "whenever (?:a|an) (.*?) becomes enchanted", "whenever (?:a|an) (.*?) you control becomes enchanted"
- [ ] Create `check_enchanted_triggers(game_state, enchanted_perm_ids: list[str])` that queues PendingTriggers
- [ ] Wire into the attach action handler (when an Aura is attached to a permanent)
- [ ] Integration tests: Aura attached fires trigger on the enchanted creature, unattaching does NOT fire, Equipment attaching does NOT fire (only Auras)
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: Medium

## Estimated Effort: M

## Notes
- "Becomes enchanted" is the creature's/player's perspective — distinct from "becomes attached" (aura's perspective)
- Only Aura subtypes cause "enchanted" state — Equipment, Fortifications don't count
- Forge's trigger: `BecomesEnchantedTrigger`
