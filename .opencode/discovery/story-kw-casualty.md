# Story: Casualty (CR 702.137)

## User Story
As an MTG engine developer, I want a new casualty keyword module with real apply() and integration tests, so that cards with casualty N work correctly in the engine.

## Context
No file exists for casualty. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.137**: "Casualty is a keyword that represents an optional additional cost. 'Casualty N' means 'As an additional cost to cast this spell, you may sacrifice a creature with power N or greater. When you do, copy this spell.'"
- **Example card**: Strangle — "Casualty 1 (As an additional cost to cast this spell, you may sacrifice a creature with power 1 or greater. When you do, copy this spell.)"
- **Rule source**: Optional additional cost with spell-copy effect

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/casualty.py` with `Casualty` class extending `CostKeyword`
- [ ] `parse_casualty(oracle_text) -> int | None` detects casualty power threshold
- [ ] `apply()` checks battlefield for creatures with power >= N controlled by caster
- [ ] For human players: queues `pending_casualty_choice` with eligible creature options
- [ ] For AI players: auto-resolves (sacrifices the lowest-power eligible creature, or skips if none)
- [ ] When paid, creates a copy of the spell on the stack during resolution
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: casualty with eligible creature, no eligible creature (can't pay), human choice queuing, AI auto-resolution, spell copy targeting, copied spell resolves
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- The sacrifice and copy both happen as part of casting the spell
- The copy may also have casualty (but you can't pay it again since the original creature is already sacrificed)
- Needs integration with the stack copy mechanism (similar to replicate/storm)
- Streets of New Capenna mechanic
