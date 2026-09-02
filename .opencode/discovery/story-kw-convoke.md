# Story: Convoke (CR 702.43)

## User Story
As an MTG engine developer, I want the Convoke keyword module to have a real `apply()` implementation with integration tests, so that spells with Convoke can be cast by tapping creatures to help pay mana costs.

## Context
The Convoke keyword module exists with basic detection logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.43a**: "Convoke is a static ability that functions while the card is on the stack. 'Convoke' means 'As an additional cost to cast this spell, you may tap any number of untapped creatures you control. Each creature tapped this way reduces the cost by {1} or by one mana of that creature's color.'"
- **CR 702.43b**: "The convoke cost reduction applies before other cost reductions."
- **Example card**: Chord of Calling — "Convoke" (tap creatures to reduce the cost; a green creature tapped this way pays {G}, any other creature pays {1})

## Acceptance Criteria
- [ ] `Convoke.apply(game_state, permanent)` implements full convoke logic: during spell declaration, queues `pending_convoke_choice` for human players with available creatures list
- [ ] AI auto-resolves by tapping creatures to maximize cost reduction (prefers colored mana matching needed colors)
- [ ] Each tapped creature reduces cost by {1} or one mana of that creature's color (colored creatures produce colored mana matching their colors, colorless creatures produce {1})
- [ ] Convoke is an additional cost applied during mana payment — cost reduction is calculated before final mana cost payment
- [ ] Tapped creatures remain tapped as normal (they are tapped as part of the cost, not as a separate action)
- [ ] Integration tests in `tests/engine/test_convoke_integration.py` with 8-15 tests
- [ ] Full regression suite passes (2792+ tests, 0 failures)

## Dependencies
- None

## Priority: Medium

## Estimated Effort: S

## Notes
- **Cost reduction mechanics**: Convoke reduces the mana cost by producing mana from each tapped creature. Colored creatures produce mana of their colors; multicolored creatures give a choice; colorless creatures produce generic. Wire into the mana payment flow in stack.py.
- **Convoke timing**: Convoke is an additional cost paid as the spell is being cast. The player chooses creatures to tap for convoke during step 6 of casting a spell (CR 601.2f/g/h). It does not use the stack.
- **Human/AI pattern**: Follow the Kicker (KW-16) pattern — queue `pending_convoke_choice` for human players with the list of eligible untapped creatures; auto-resolve for AI using a greedy algorithm that maximizes color matching.
- **AI heuristic**: Match tapped creature colors to the spell's remaining mana cost. Prioritize creatures whose color identity matches needed colors. Fall back to tapping any remaining untapped creatures for generic reduction.
