# Story: Damage Dealt Once Trigger (CR 119.3)

## User Story
As an MTG engine developer, I want a general damage-dealt trigger pattern with check function and engine wiring, so that cards with "Whenever ~ deals damage" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. This is a general trigger that fires whenever a source deals damage (combat or non-combat) to any target, distinct from existing combat damage triggers.

### Comprehensive Rules Grounding
- **CR 119.3**: "Damage may be dealt as a result of combat or as a result of a spell or ability. Some effects deal damage directly."
- **Example card**: *Niv-Mizzet, the Firemind* — "Whenever Niv-Mizzet, the Firemind deals damage to any target, draw a card."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into damage-dealing flow in stack.py (`_deal_damage()`)
- [ ] Integration tests covering combat and non-combat damage
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- This is a "whenever ~ deals damage" trigger — general damage dealing, not specific to combat or a particular target type.
- Must be wired into `_deal_damage()` in stack.py where all damage resolution happens.
- Existing combat damage triggers in check_damage_triggers may already handle some cases; ensure no double-firing with this new general pattern.
- Example cards: *Niv-Mizzet, the Firemind*, *Chandra, Torch of Defiance*, *Guttersnipe*, *Spellheart Chimera*.
