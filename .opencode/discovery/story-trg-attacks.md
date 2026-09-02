# Story: Attacks Trigger Refinement (CR 508.1)

## User Story
As an MTG engine developer, I want refined attack trigger patterns that cover the full range of "whenever ~ attacks" variants (alone, with other creatures, specific targets), so that all cards with attack-triggered abilities fire correctly.

## Context
A basic `ATTACK_TRIGGER_PATTERNS` and `check_attack_triggers()` exist in triggers.py and are wired into combat/core.py's `declare_attackers()`. However, the patterns don't cover common Forge-level granularity: "whenever ~ attacks alone", "whenever ~ attacks a player", "whenever ~ attacks a planeswalker", or "whenever a creature attacks with another creature" variants. Cards with these specific patterns may miss or double-fire.

### Comprehensive Rules Grounding
- **CR 508.1**: "First, the active player chooses which of their creatures that they control, if any, will attack."
- **CR 508.6**: "If a creature is attacking a planeswalker, the attacking creature's controller announces which planeswalker it's attacking."
- **Game event**: A creature is declared as an attacker during declare attackers step
- **Example card**: *Duelist's Heritage* — "Whenever a creature attacks, you may have it gain double strike until end of turn."

## Acceptance Criteria
- [ ] Audit existing ATTACK_TRIGGER_PATTERNS against Forge's attack trigger list — identify missing sub-patterns
- [ ] Add patterns for: "attacks alone", "attacks a player", "attacks a planeswalker", "attacks with other creatures"
- [ ] Ensure `check_attack_triggers()` gets attack target info (which player/planeswalker is being attacked)
- [ ] Integration tests for each new sub-pattern
- [ ] No regressions in existing attack trigger tests

## Dependencies
- None (refinement of existing pattern)

## Priority: High

## Estimated Effort: M

## Notes
- The existing ATTACK_TRIGGER_PATTERNS (5 regexes) cover basic cases but lack specificity for "alone" and "with" variants
- Attack target info (attacking_player_name vs attacking_planeswalker_name) must be passed to the check function
- Forge's trigger: `AttacksTrigger`, `AttacksAloneTrigger`, `AttacksPlayerTrigger`, `AttacksPlaneswalkerTrigger`
