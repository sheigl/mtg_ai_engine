# Story: Crewed / Saddled / Becomes a Creature Trigger (CR 702.121a)

## User Story
As an MTG engine developer, I want a "crewed" or "saddled" trigger pattern with check function and engine wiring, so that Vehicle and Mount permanents that trigger "whenever ~ becomes a creature" fire correctly.

## Context
No "crewed/saddled" trigger pattern exists in triggers.py. Vehicles (CR 702.121a) become creatures when crewed, and some Vehicles have triggers when they become crewed (i.e., become creatures). Similarly for Saddled (Mounts). This is distinct from being a creature inherently — it fires when a non-creature artifact becomes a creature.

### Comprehensive Rules Grounding
- **CR 702.121a**: "Crew is an activated ability of a Vehicle. '[Quantity] Crew [N]' means 'Tap any number of untapped creatures you control with total power N or more: This permanent becomes an artifact creature until end of turn.'"
- **Game event**: A Vehicle/Mount becomes a creature after being crewed/saddled
- **Example card**: *Cultivator's Caravan* — "Whenever ~ becomes a creature, add one mana of any color."

## Acceptance Criteria
- [ ] Create `CREWED_TRIGGER_PATTERNS` list with regexes matching: "whenever (?:this|~) becomes crewed", "whenever (?:this|~) becomes a creature", "whenever (?:this|~) becomes saddled"
- [ ] Create `check_crewed_triggers(game_state, crewed_perm_ids: list[str])` that queues PendingTriggers
- [ ] Wire into the crew/saddle activation handler (where the permanent becomes a creature)
- [ ] Integration tests: crewing a Vehicle fires trigger, uncrewing (end of turn) does NOT fire, permanent was already a creature does NOT fire
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: Medium

## Estimated Effort: M

## Notes
- Also covers "whenever ~ becomes saddled" for Mount creatures (OTJ 2024 new mechanic)
- "Becomes a creature" is a broader pattern — covers any non-creature becoming a creature via any effect
- Forge's trigger: `CrewedTrigger`, `SaddledTrigger`, `BecomesCreatureTrigger`
