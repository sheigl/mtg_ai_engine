# Story: Explores Trigger (CR 701.33)

## User Story
As an MTG engine developer, I want an "explores" trigger pattern with check function and engine wiring, so that cards with "when ~ explores" triggered abilities fire correctly.

## Context
No explore trigger pattern exists in triggers.py. The explore mechanic (CR 701.33) was introduced in Ixalan block and appears on many creatures. When a creature explores, its controller reveals the top card of their library, may put it into their hand if it's a land, and otherwise puts a +1/+1 counter on the exploring creature.

### Comprehensive Rules Grounding
- **CR 701.33**: "To explore, a player reveals the top card of their library and checks its card type(s). If that card is a land card, they put that card into their hand. Otherwise, they put a +1/+1 counter on the exploring creature, and may put the card into their graveyard or put it back on top."
- **Game event**: A creature or permanent explores
- **Example card**: *Merfolk Branchwalker* — "When ~ explores, you may draw a card."

## Acceptance Criteria
- [ ] Create `EXPLORE_TRIGGER_PATTERNS` list with regexes matching: "when(?:ever)? (?:this|~) explores", "whenever a creature you control explores"
- [ ] Create `check_explore_triggers(game_state, explored_perm_ids: list[str])` that queues PendingTriggers
- [ ] Wire into the explore resolution handler in stack.py
- [ ] Integration tests: exploring fires trigger, non-explore actions do NOT fire
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: Medium

## Estimated Effort: M

## Notes
- Explore is an action, not a keyword ability — creatures have "When ~ explores, ..." as a triggered ability
- The explore action itself has sub-effects (draw land or put counter), but the trigger fires whenever the action is taken
- Forge's trigger: `ExploredTrigger`
