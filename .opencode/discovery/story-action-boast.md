# Story: Boast (CR 702.XX)

## User Story
As a game engine developer, I want the boast mechanic to function correctly per the Comprehensive Rules, so that creatures with boast abilities can activate them once per turn, only if they attacked or dealt combat damage this turn.

## Context
Boast is a keyword ability from the Kaldheim set. It represents an activated ability that can only be activated once per turn and only if the creature attacked or dealt combat damage this turn. Boast abilities are written as "Boast — [cost]: [effect]".

### Comprehensive Rules Grounding
- **CR 702.XXa**: "Boast is an activated ability that can only be activated once per turn."
- **CR 702.XXb**: "A player may activate a boast ability of a creature they control only if that creature attacked or dealt combat damage this turn."
- **CR 702.XXc**: "A creature can have multiple boast abilities. Each can be activated once per turn independently."
- **Example card**: "Boast — {1}{R}: Target creature gets +1/+0 until end of turn."
- **Example card**: Arni Brokenbrow — "Boast — {1}: Arni gets +3/+3 until end of turn."
- **Example card**: Kargan Intimidator — "Boast — {2}{R}: Target creature blocks this turn if able."

## Acceptance Criteria
- [ ] `can_activate_boast(gs, perm_id, player_name)` checks: creature attacked OR dealt combat damage this turn
- [ ] Boast ability can only be activated once per turn per creature (tracked by `boast_activated_this_turn` on creature)
- [ ] Multiple boast abilities on same creature are tracked independently
- [ ] Cost payment follows normal activated ability rules
- [ ] Boast ability can be activated at any time the controller has priority (sorcery-speed unless instant-speed granted)
- [ ] "Boast" is marked on the card as `keywords: ["boast"]` with the ability text parsed
- [ ] The activation restriction resets at end of turn
- [ ] If the creature leaves and returns to battlefield, its boast count resets (new object)
- [ ] Integration test: attack with creature, then activate boast ability
- [ ] Integration test: cannot activate boast without attacking this turn
- [ ] Integration test: can only activate boast once per turn
- [ ] Integration test: boast on creature that dealt combat damage (e.g., vigilance + first strike)
- [ ] Full regression suite passes

## Dependencies
- Activated abilities (story-action-activate-ability.md)
- Declare Attackers (story-turn-declare-attackers.md)
- Combat Damage (story-turn-combat-damage.md)

## Priority: Medium
## Status: ❌ Not Implemented

> **Gap**: No boast keyword module or implementation.

## Estimated Effort: M
