# Story: Blocks Trigger Refinement (CR 509.1)

## User Story
As an MTG engine developer, I want refined block trigger patterns covering "whenever ~ blocks" variants (alone, with other creatures, specific attacker), so that all cards with block-triggered abilities fire correctly.

## Context
A basic `BLOCK_TRIGGER_PATTERNS` and `check_block_triggers()` exist in triggers.py and are wired into combat/core.py's `declare_blockers()`. The patterns may not cover specific sub-variants like "whenever ~ blocks alone" or "whenever ~ blocks a creature with flying" that Forge supports.

### Comprehensive Rules Grounding
- **CR 509.1**: "First, the defending player chooses which of their creatures, if any, will block."
- **Game event**: A creature is declared as a blocker during declare blockers step
- **Example card**: *Guardian of the Gateless* — "Whenever ~ blocks, it gets +1/+1 until end of turn for each creature blocking it."

## Acceptance Criteria
- [ ] Audit existing BLOCK_TRIGGER_PATTERNS against Forge block trigger list
- [ ] Add patterns for: "blocks alone", "blocks a creature with flying/reach", "blocks with other creatures"
- [ ] Ensure `check_block_triggers()` receives blocker assignment info
- [ ] Integration tests for new sub-patterns
- [ ] No regressions

## Dependencies
- None (refinement of existing pattern)

## Priority: High

## Estimated Effort: M

## Notes
- The existing BLOCK_TRIGGER_PATTERNS (3 regexes) cover basic cases
- Forge's trigger: `BlocksTrigger`, `BlocksAloneTrigger`, `BlocksCreatureWithFlyingTrigger`
- Combat damage step wiring may need the blocker's assigned attacker info
