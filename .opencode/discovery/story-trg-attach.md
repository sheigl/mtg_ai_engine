# Story: Attach Trigger (CR 702.5 / CR 702.54a)

## User Story
As an MTG engine developer, I want attach triggers wired into the engine event flow, so that cards with "whenever this becomes attached to a creature" abilities fire correctly instead of silently no-op'ing.

## Context
The `check_attach_triggers()` function already exists in triggers.py but is NOT called from anywhere in the engine's event flow. This needs wiring when equip/fortify attaches an Equipment or Fortification to a target.

### Comprehensive Rules Grounding
- **CR 702.5**: "To attach Equipment to a creature, activate its equip ability."
- **CR 702.54a**: "Fortify is an activated mana cost that attaches Fortification to target land you control." (Note: CR reference for fortify attachment)
- Example card: *Sword of the Paruns* — "Whenever Sword of the Paruns becomes attached, its equipped creature gets +1/+1 and gains vigilance and lifelink until end of turn."

## Acceptance Criteria
- [ ] Call `check_attach_triggers()` from equip resolution when equipment attaches to creature (after `attached_to` field is updated)
- [ ] Also call from fortify resolution (when that keyword is implemented in story-kw-fortify.md)
- [ ] Pass aura/equipment perm_id and attached_to_perm_id to the check function
- [ ] Integration test: equip fires attached trigger, unequip/death fires unattach trigger

## Dependencies
- None (uses existing check function; only adds call sites)

## Priority: High

## Estimated Effort: S (~0.25 day including tests)

## Notes
- **Attach vs Unattach**: Both attach and unattach triggers should be supported. Attach fires when `attached_to` changes from null to a perm_id. Unattach fires when `attached_to` changes from a perm_id to null (e.g., equipment leaves battlefield, creature dies). Consider wiring both into the same attachment state change handler.
