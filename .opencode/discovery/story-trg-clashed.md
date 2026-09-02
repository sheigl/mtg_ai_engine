# Story: Clashed Trigger (CR 701.23)

## User Story
As an MTG engine developer, I want a clashed trigger pattern with check function and engine wiring, so that cards with "When you clash" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Clash" is a mechanic from the Lorwyn/Shadowmoor block where two players reveal the top card of their library and compare mana values.

### Comprehensive Rules Grounding
- **CR 701.23**: "To clash two players, each of those players reveals the top card of their library, then puts that card on top of their library if it has the highest mana value among cards revealed this way, or into their graveyard otherwise. A player wins a clash if they revealed a card with a higher mana value."
- **Example card**: *Judge of the Dawn* — "When you clash and win, you may return target creature to its owner's hand."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into clash resolution flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Clash involves two players revealing the top card of their library and comparing mana values.
- The trigger may fire on "when you clash and win" (won the comparison) or "when you clash" (regardless of outcome).
- Distinguish between winning, losing, and tying in clash comparisons.
- Example cards: *Judge of the Dawn*, *Briarhorn*, *Faerie Tauntings*, *Squeaking Pie Snitch*.
