# Story: Transformed "Becomes a Creature" Trigger (CR 711.3)

## User Story
As an MTG engine developer, I want refined "transforms" trigger patterns covering "whenever a permanent transforms" and "whenever a permanent transforms into a creature" variants, so that all dual-faced card triggers fire correctly.

## Context
The `TRANSFORMED_TRIGGER_PATTERNS` and `check_transformed_triggers()` exist in triggers.py but are NOT wired into the engine's transform action flow. Additionally, the patterns may not cover the "transforms into a creature" sub-variant (for non-creatures that transform into creatures).

### Comprehensive Rules Grounding
- **CR 711.3**: "When a double-faced card transforms, it's turned from one face to the other."
- **Game event**: A double-faced card changes from one face to the other via a transform action
- **Example card**: *Docent of Perfection* — "Whenever a permanent transforms into a creature, ..."

## Acceptance Criteria
- [ ] Wire `check_transformed_triggers(gs, perm_id)` into zones.py's transform handler (MDFC transform or day/night change)
- [ ] Add additional patterns for: "transforms into a creature", "transforms for the first time"
- [ ] Capture return value (`gs = check_transformed_triggers(...)`)
- [ ] Integration tests: transforming fires trigger, non-transform permanents do NOT fire, day/night change counts as transform
- [ ] No regressions

## Dependencies
- None (wiring existing check function + refinement)

## Priority: Medium

## Estimated Effort: S

## Notes
- The existing check function exists but is dead code — needs a call site in the transform action
- Transform happens via: MDFC transform activated ability, day/night change, or other transform effects
- Forge's trigger: `TransformedTrigger`, `TransformedIntoCreatureTrigger`
