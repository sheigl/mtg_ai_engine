# Story: Additional Missing Trigger Patterns — Scry, Cycled, Abandoned, Mutates, Loyalty Change

## User Story
As an MTG engine developer, I want five additional trigger patterns implemented with regex detection, check functions, and engine wiring, so that cards with these triggered abilities fire correctly instead of silently no-op'ing.

## Context
Five more trigger categories are completely missing from triggers.py (no regex patterns, no check functions) but appear frequently enough in modern MTG to warrant implementation:

1. **Scry** — "Whenever you scry" / "Whenever a player scrys" — Needed for cards like [[Rest in Peace]] ("Whenever a player would scry N, that player scries N-1 instead"), [[Teferi, Time Raveler]], [[Rhoda, Geist Avenger]].

2. **Cycled** — "Whenever you cycle a card" / "Whenever a card is cycled" — Distinct from generic discard; needed for cycling archetypes like [[Windreaper Falcon]] ("Whenever you cycle a card, put a charge counter on Windreaper Falcon"), [[Goblin Electromancer]].

3. **Abandoned** — "Whenever a permanent is abandoned" — MDFC-specific trigger (Phyrexia sets). When the back face of an MDFC is put into graveyard from battlefield, it's "abandoned." Needed for cards like [[The Glorious Anthem]].

4. **Mutates** — "Whenever this creature mutates" / "Whenever a creature mutates" — Stack creatures mechanic (Amonkhet block, reprinted in Phyrexia). When a mutating spell resolves on top of another creature, it merges and the combined creature triggers "mutates."

5. **Loyalty Change** — "Whenever loyalty is put on [planeswalker]" / "Whenever [planeswalker]'s loyalty changes" — Needed for planeswalker counter interactions like [[Teferi, Time Raveler]], [[Karn, Scion of Urza]].

## Acceptance Criteria

### Scry Trigger
- [ ] Add `SCRY_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever you scry", "whenever a player scrys?", "whenever .*? scries?"
- [ ] Create `check_scry_triggers(game_state, player_name, amount)` function that iterates battlefield permanents and queues matching PendingTriggers with `trigger_type="scry"` including the scry amount in trigger_data
- [ ] Wire into stack.py's scry resolution: when a scry effect resolves (look at top N cards, reorder), call `check_scry_triggers()` before modifying the library
- [ ] Integration tests: scry fires trigger, non-scry effects do NOT fire, scry amount passed to trigger

### Cycled Trigger
- [ ] Add `CYCLED_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever you cycle (?:a|an) .*?", "whenever a card is cycled", "whenever (?:this|~) is cycled"
- [ ] Create `check_cycled_triggers(game_state, player_name, cycled_card)` function that iterates battlefield permanents and queues matching PendingTriggers with `trigger_type="cycled"` including the cycled card's data in trigger_data
- [ ] Wire into cycling resolution: when a card is cycled (discarded via cycling cost), call `check_cycled_triggers()` after the card moves to graveyard. Distinguish from regular discard by checking if the discard reason is "cycle"
- [ ] Integration tests: cycle fires cycled trigger, regular discard does NOT fire cycled trigger, self-referential guard

### Abandoned Trigger
- [ ] Add `ABANDONED_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever (?:a|an) .*? is abandoned", "whenever a permanent you control is abandoned"
- [ ] Create `check_abandoned_triggers(game_state, perm_id, controller)` function that iterates battlefield permanents and queues matching PendingTriggers with `trigger_type="abandoned"`
- [ ] Wire into MDFC graveyard flow: when the back face of an MDFC permanent moves from battlefield to graveyard (via destruction), call `check_abandoned_triggers()` in addition to normal death triggers
- [ ] Integration tests: MDFC back face going to graveyard fires abandoned trigger, non-MDFC death does NOT fire abandoned trigger

### Mutates Trigger
- [ ] Add `MUTATES_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever this creature mutates", "whenever a creature you control mutates", "whenever (?:a|an) .*? mutates"
- [ ] Create `check_mutates_triggers(game_state, mutated_perm_id, controller)` function that iterates battlefield permanents and queues matching PendingTriggers with `trigger_type="mutates"`
- [ ] Wire into mutate resolution: when a mutating spell resolves on top of another creature (merge logic in stack.py), call `check_mutates_triggers()` after the merge completes
- [ ] Integration tests: mutate fires trigger, non-mutate ETB does NOT fire mutates trigger

### Loyalty Change Trigger
- [ ] Add `LOYALTY_CHANGE_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever loyalty is put on .*?", "whenever .*?'s loyalty changes", "whenever a planeswalker you control gets.*?loyalty counters"
- [ ] Create `check_loyalty_change_triggers(game_state, perm_id, old_loyalty, new_loyalty)` function that iterates battlefield permanents and queues matching PendingTriggers with `trigger_type="loyalty_change"` including loyalty delta in trigger_data
- [ ] Wire into planeswalker loyalty ability resolution: when a loyalty ability is activated (adding or removing loyalty counters), call `check_loyalty_change_triggers()` after the counter change
- [ ] Integration tests: loyalty increase fires trigger, loyalty decrease fires trigger, non-planeswalker effects do NOT fire

### Cross-cutting requirements
- [ ] All new trigger patterns follow the existing pattern in triggers.py: regex list + dedicated check function that returns new GameState via `model_copy(update={"pending_triggers": ...})`
- [ ] All new trigger types are dispatched through `_resolve_triggered_effect()` in stack.py using the effect description text resolution pipeline
- [ ] Full test suite passes: 2792+ regression tests, 0 failures (3 skipped + 13 xfailed expected)
- [ ] Each trigger type has at least 4 integration tests covering: positive fire case, negative no-fire case, self-referential guard, data passed to trigger

## Dependencies
- None (independent of other stories; uses existing trigger infrastructure in triggers.py and stack.py)
- Scry trigger depends on scry effect resolution having a call site in stack.py
- Cycled trigger depends on cycling discard being distinguishable from regular discard (reason field in zone change event)

## Priority: Medium

## Estimated Effort: L (5 triggers × ~0.4 day each = 2 days, plus tests)

## Notes
- **Scry trigger timing**: Scry effects modify the library order. The trigger should fire BEFORE the library is modified, so that replacement effects like Rest in Peace can reduce the scry amount before it takes effect. Consider passing the scry amount as a mutable reference or using a two-phase approach: (1) check triggers and collect modifications, (2) apply final scry amount to library.
- **Cycled vs Discard distinction**: The key is that cycling is an activated ability with a specific cost, while discard can happen from many sources. Use the zone change event's `reason` field — set reason="cycle" when a card is discarded via cycling, and only fire cycled triggers for reason="cycle". Regular discard uses reason="discard".
- **Abandoned vs Death distinction**: Abandoned fires specifically when an MDFC back face goes to graveyard. This is distinct from normal death (which also fires). Both should fire — abandoned is an additional trigger specific to MDFCs. Check if the dying permanent has `is_mdfc_back_face` flag before calling `check_abandoned_triggers()`.
- **Mutates merge logic**: Mutate is a special targeting mode where the spell merges with the target creature rather than entering as a separate permanent. The engine needs mutate resolution in stack.py that combines the two permanents' characteristics (union of abilities, highest P/T). The mutates trigger fires after this merge completes.
- **Loyalty change tracking**: Planeswalkers have a `loyalty` field on their Permanent model. When a loyalty ability activates, the loyalty counter is added or removed. Track the before/after values to compute the delta for triggers that care about "whenever loyalty changes" vs "whenever N loyalty counters are put on."
