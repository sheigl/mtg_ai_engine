# Story: Equip (CR 702.6)

## User Story
As an MTG engine developer, I want the Equip keyword module to have a real `apply()` implementation with integration tests, so that Equipment cards can be attached to creatures at sorcery speed with correct P/T bonuses.

## Context
The Equip keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.6a**: "Equip is an activated ability of Equipment cards. 'Equip {cost}' means '{cost}: Attach this permanent to target creature you control. Activate this ability only any time you could cast a sorcery.'"
- **CR 702.6b**: "An equipment's equip ability can't be activated if the equipment is already attached to a creature."
- **Example card**: Sword of Fire and Ice — "Equipped creature gets +2/+2 and has protection from red and from blue. Equip {2}"

## Acceptance Criteria
- [ ] `Equip.apply(game_state, permanent)` implements full equip logic: validates equipment is on battlefield and not already attached; queues `pending_equip_choice` for human players with valid target list
- [ ] AI auto-resolves by equipping to highest-power creature controller controls
- [ ] Equipment attaches to target creature (updates `attached_to` field on Permanent)
- [ ] Equipped creature gains static P/T bonuses from equipment's oracle text (+N/+N patterns) via layer 7b P/T modifications
- [ ] Sorcery-speed timing: equip can only be activated during controller's main phase when stack is empty
- [ ] Equipment cannot be equipped to a creature it's already attached to (CR 702.6b)
- [ ] Integration tests in `tests/engine/test_equip_integration.py` with 8-15 tests
- [ ] Full regression suite passes (2792+ tests, 0 failures)

## Dependencies
- None

## Priority: High

## Estimated Effort: M

## Notes
- **Equip timing**: Equip is sorcery-speed only. The legal actions system in `_compute_legal_actions` must gate equip to main phase with empty stack. Reference how other activated abilities are gated.
- **P/T bonus parsing**: Equipment oracle text contains patterns like "+3/+1" or "gets +N/+N". Parse these at resolution time and apply via the layers system (layer 7b) on the equipped creature. Store as `power_bonus`/`toughness_bonus` on Permanent.
- **Attachment tracking**: The Permanent model already has `attached_to: Optional[str]` field. When equipment attaches, set `equipment_perm.attached_to = target_creature_perm_id`. Also update the target's `attachments` list.
