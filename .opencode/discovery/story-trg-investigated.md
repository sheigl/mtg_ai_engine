# Story: Investigated Trigger (CR 701.32)

## User Story
As an MTG engine developer, I want an "investigated" trigger pattern with check function and engine wiring, so that cards with "whenever you investigate" triggered abilities fire correctly.

## Context
No investigated trigger pattern exists in triggers.py. The investigate mechanic (CR 701.32) creates Clue artifact tokens that can be sacrificed for card draw. Cards like [[Tamiyo's Journal]] have "whenever you investigate" as a cost-reduction ability.

### Comprehensive Rules Grounding
- **CR 701.32**: "To investigate, a player creates a Clue token. Clue is an artifact token with '{2}, Sacrifice this artifact: Draw a card.'"
- **Game event**: A Clue artifact token is created
- **Example card**: *Tamiyo's Journal* — "At the beginning of your upkeep, investigate."

## Acceptance Criteria
- [ ] Create `INVESTIGATED_TRIGGER_PATTERNS` list with regexes matching: "whenever you investigate", "whenever a player investigates"
- [ ] Create `check_investigated_triggers(game_state, player_name: str)` that iterates battlefield permanents and queues PendingTriggers
- [ ] Wire into the investigate action handler in stack.py (where Clue tokens are created)
- [ ] Integration tests: investigating fires trigger, creating non-Clue tokens does NOT fire
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: High

## Estimated Effort: S

## Notes
- Investigate is explicitly "create a Clue token" — differentiate from generic token creation
- The Clue token has a specific activated ability ({2}, Sacrifice: Draw a card)
- Forge's trigger: `InvestigatedTrigger`
- Already identified as P0 in SPRINT7-P0-missing-triggers.md
