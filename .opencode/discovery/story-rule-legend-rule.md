# Story: Legend Rule (CR 704.5j)

## User Story
As a game engine developer, I want the legend rule to be enforced as a state-based action, so that when a player controls two or more legendary permanents with the same name, they choose one to keep and put the rest into their owner's graveyard.

## Context
The legend rule is a state-based action (CR 704.5j) that enforces the "only one legendary permanent with a given name" restriction. When a player controls multiple legendary permanents with the same name, they choose one to keep and sacrifice the rest. The player CHOOSES which to keep (changed in a 2013 rules update from "both destroyed").

### Comprehensive Rules Grounding
- **CR 704.5j**: "If a player controls two or more legendary permanents with the same name, that player chooses one and puts the others into their owner's graveyard."
- **CR 704.5k**: "If a player controls two or more legendary planeswalkers with the same planeswalker type, that player chooses one and puts the others into their owner's graveyard."
- **Example card**: Two copies of "Squee, the Immortal" on the battlefield under the same player's control

## Acceptance Criteria
- [x] Legend rule check is a state-based action in the SBA loop
- [x] After any permanent enters the battlefield, the legend rule is checked
- [x] If a player controls two+ legendary permanents with the same name, the player chooses one to keep
- [x] The unchosen permanents are put into their owner's graveyard (not sacrificed, not destroyed)
- [x] State-based action: happens automatically, no player receives priority until resolved
- [x] The "choose" is the player's choice (not "sacrifice all but one")
- [x] Planeswalker uniqueness rule: same planeswalker type also checked (CR 704.5k)
- [x] Supertype (legendary) matters, not card type alone
- [x] Tokens with legendary names are also affected by the legend rule
- [x] Copies (e.g., from "Copy target creature") trigger the legend rule if they're legendary
- [x] Integration tests cover: two same-name legendaries, three+ legendaries, legendary token rule, planeswalker type rule, "no choice" when only one
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- Story: State-Based Actions (CR 704) — legend rule is an SBA

## Priority: Medium

## Status: ✅ Complete

## Estimated Effort: M

## Notes
- Current state: the engine may have partial legend rule support — this story formalizes it as an SBA
- The 2013 rules change is important: player chooses which to keep, rather than sacrificing both
- Planeswalker uniqueness rule (CR 704.5k) checks planeswalker TYPES (e.g., "Jace"), not names
- The put-into-graveyard effect does NOT trigger "when you sacrifice" triggers — it's not a sacrifice
- Legendary supertype is checked, not just creature type "Legend" — applies to legendary artifacts, enchantments, etc.
- Rule applies to permanents on the battlefield only — having multiple copies in hand/graveyard is fine
