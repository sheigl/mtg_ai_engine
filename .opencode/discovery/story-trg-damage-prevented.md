# Story: Damage Prevented Once Trigger (CR 119.3)

## User Story
As an MTG engine developer, I want a damage-prevented trigger pattern so that cards with "if damage would be prevented" or "whenever damage is prevented" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 119.3**: "Damage may be prevented by effects. If damage is prevented, it is not dealt."
- **Example card**: "If damage would be prevented, you may have that damage be dealt instead." (e.g., Shaman's Trance style effects)

## Acceptance Criteria
- [ ] Add `DAMAGE_PREVENTED_TRIGGER_PATTERNS` regex patterns for "whenever damage is prevented" and "if damage would be prevented"
- [ ] Add `check_damage_prevented_triggers()` check function
- [ ] Wire into the engine damage prevention / replacement path
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M
