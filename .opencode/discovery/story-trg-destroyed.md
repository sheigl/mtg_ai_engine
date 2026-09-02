# Story: Destroyed Trigger (CR 701.7)

## User Story
As an MTG engine developer, I want a "destroyed" trigger pattern with check function and engine wiring, so that cards with "when ~ is destroyed" triggered abilities fire correctly, distinct from generic death triggers.

## Context
Only generic `DEATH_TRIGGER_PATTERNS` exist in triggers.py (covering "dies" broadly). No specific "destroyed" pattern exists that distinguishes destroy effects from sacrifice or -1/-1 counter state-based action deaths. Per CR 701.7, "destroy" is a specific action — cards that say "when ~ is destroyed" should only fire when a destroy effect resolves, not on sacrifice or lethal damage.

### Comprehensive Rules Grounding
- **CR 701.7**: "To destroy a permanent, an effect or state-based action moves it to the graveyard. Being destroyed is different from being sacrificed."
- **Game event**: A destroy effect (or lethal damage SBA) causes a permanent to go to graveyard
- **Example card**: *Tilling Treefolk* — "When ~ is destroyed, you may return target land card from your graveyard to your hand."

## Acceptance Criteria
- [ ] Create `DESTROYED_TRIGGER_PATTERNS` list with regexes matching: "when(?:ever)? (?:this|~) is destroyed", "whenever (?:a|an) (.*?) is destroyed"
- [ ] Create `check_destroyed_triggers(game_state, destroyed_perm_ids: list[str])` that iterates battlefield permanents and queues PendingTriggers
- [ ] Wire into zones.py's destroy path (where `reason="destroy"` in zone change event)
- [ ] Ensure this fires ONLY for destroy effects, NOT for sacrifice or SBA death from -1/-1 counters
- [ ] Integration tests: destroyed by spell fires, destroyed by combat damage fires, sacrificed does NOT fire, die from -1/-1 counters does NOT fire
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: High

## Estimated Effort: M

## Notes
- **Distinction from death**: Death trigger fires on ANY permanent going from battlefield to graveyard. Destroyed trigger fires only when the zone change reason is "destroy".
- **Two destroy paths**: Effects that explicitly say "destroy" (via _apply_single_effect_text with "destroy" pattern) AND lethal damage state-based actions (0 toughness) both cause "destroy" type death.
- **Forge's trigger**: `DestroyedTrigger` — Forge distinguishes this from `DiesTrigger`.
