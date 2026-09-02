# Story: Land Played / Landfall Trigger (CR 305.1)

## User Story
As an MTG engine developer, I want refined land play trigger patterns that cover all "whenever a land enters under your control" variants, so that all landfall and land-play triggered abilities fire correctly.

## Context
The `LANDFALL_TRIGGER_PATTERNS` exist in triggers.py and are wired into zones.py's `_on_zone_change()` listener. However, the patterns may not cover specific sub-variants like "whenever a land is put into your graveyard from the battlefield" (as distinct from entering), or {N} or more lands in a turn.

### Comprehensive Rules Grounding
- **CR 305.1**: "A player may play a land from their hand during their main phase by putting it onto the battlefield."
- **CR 305.4**: "Effects may also put lands onto the battlefield."
- **Game event**: A land card or land permanent enters the battlefield under a player's control
- **Example card**: *Lotus Cobra* — "Whenever a land enters under your control, add one mana of any color."

## Acceptance Criteria
- [ ] Audit existing LANDFALL_TRIGGER_PATTERNS for missing sub-patterns
- [ ] Ensure patterns cover: "whenever a land enters the battlefield", "landfall" keyword, "whenever you play a land", "whenever a land is put into a graveyard from the battlefield"
- [ ] Verify wiring in `_on_zone_change()` works for all land types (basic, non-basic, tokens)
- [ ] Integration tests for each sub-pattern
- [ ] No regressions

## Dependencies
- None (refinement of existing pattern)

## Priority: High

## Estimated Effort: S

## Notes
- The existing 3-pattern LANDFALL list covers basic cases but may need expansion
- Forge's trigger: `LandfallTrigger`, `LandPlayedTrigger`, `LandEnteredTrigger`
- Some cards care about "one or more lands" — the trigger should fire once per land entry event
