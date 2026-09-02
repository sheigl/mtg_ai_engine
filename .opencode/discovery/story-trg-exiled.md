# Story: Exiled Trigger (CR 701.8)

## User Story
As an MTG engine developer, I want an "exiled" trigger pattern with check function and engine wiring, so that cards with "when ~ is exiled" triggered abilities fire correctly.

## Context
No exile trigger pattern exists in triggers.py. Per CR 701.8, exile is a specific zone change from anywhere to the exile zone. Cards like [[Ulamog, the Ceaseless Hunger]] exile permanents, and some cards trigger when permanents are exiled. This is distinct from death (battlefield→graveyard).

### Comprehensive Rules Grounding
- **CR 701.8**: "To exile a card, a player moves it from its current zone to the exile zone."
- **Game event**: A card or permanent moves from any zone to exile
- **Example card**: *Procession of the Breadfruit* — "Whenever a creature you control is exiled, you may draw a card."

## Acceptance Criteria
- [ ] Create `EXILED_TRIGGER_PATTERNS` list with regexes matching: "when(?:ever)? (?:this|~) is exiled", "whenever (?:a|an) (.*?) you control is exiled"
- [ ] Create `check_exiled_triggers(game_state, exiled_perm_ids: list[str])` that iterates battlefield permanents and queues PendingTriggers
- [ ] Wire into zones.py's `move_card_to_zone()` or `move_permanent_to_zone()` when `to_zone="exile"`
- [ ] Integration tests: exile spell fires trigger, non-exile zone changes do NOT fire, self-referential guard
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: High

## Estimated Effort: M

## Notes
- **Many exile paths**: Exile happens via exile effects, suspend (exile with time counters), delve (exile as cost), escape (exile from graveyard), etc.
- **Zone tracking**: Consider if this should fire for any zone→exile (library, hand, graveyard, stack→exile) or just battlefield→exile
- **Forge's trigger**: `ExiledTrigger`, `ExiledFromGraveyardTrigger`, `ExiledFromBattlefieldTrigger` — may need sub-types
- Some cards say "whenever a card is exiled from your graveyard" — that's a separate sub-pattern
