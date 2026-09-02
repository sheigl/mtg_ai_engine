# Story: Remaining Stub Keywords — Unearth, Transmute, Replicate, Surge, Extort, Scavenge, Counter, Meld

## User Story
As an MTG engine developer, I want the remaining stub keyword modules (not covered by Sprint 7 P0/P1 stories) to have real `apply()` implementations with integration tests, so that games using these keywords produce correct game state instead of silently no-op'ing.

## Context
Eight keyword files exist in `mtg_engine/ability/keywords/` with detection/parsing but NOOP or partial `apply()` methods. These were not included in the Sprint 7 P0 (common) or P1 (casting costs) stories:

1. **Unearth** (`unearth.py`) — Detection + parsing done, `apply()` returns `game_state`. Unearth {cost} means "Return this card from your graveyard to battlefield. It gains haste. Exile at end of turn or if leaves battlefield." (CR 702.75)

2. **Transmute** (`transmute.py`) — Has `transmute()` helper but `apply()` returns `game_state`. Transmute N means "Discard this card: Search your library for up to N cards with the same mana cost, reveal them, put one into your hand and the rest into the graveyard, then shuffle." (CR 702.98)

3. **Replicate** (`replicate.py`) — Detection + parsing done, `apply()` returns `game_state`. Replicate means "Whenever this enters, create a copy of this spell for each nonland permanent an opponent controls. You may choose new targets for the copies." (CR 702.63)

4. **Surge** (`surge.py`) — Detection + parsing done, `apply()` returns `game_state`. Surge {cost} means "You may pay this spell's surge cost rather than its mana cost if you or a teammate have cast another spell this turn." (CR 702.138b)

5. **Extort** (`extort.py`) — Detection + parsing done, `apply()` returns `game_state`. Extort {cost} means "Whenever you cast an instant or sorcery spell, each opponent may pay {cost}. If an opponent doesn't, you gain 2 life and that player loses 2 life." (CR 702.63b)

6. **Scavenge** (`scavenge.py`) — Detection + parsing done, `apply()` returns `game_state`. Scavenge N means "Exile target creature card from a graveyard: This creature gets +N/+0 until end of turn." (CR 702.138a)

7. **Counter** (`counter.py`) — Has `apply_counter()` but main `apply()` returns `game_state`. Counter spell is the most basic interaction — counter target spell. (CR 701.5)

8. **Meld** (`meld.py`) — Detection + parsing done, `apply()` returns `game_state`. Meld means two cards in hand/graveyard combine to enter battlefield as a third card. (CR 702.146b)

## Acceptance Criteria

### Unearth (CR 702.75)
- [ ] `UnearthKeyword.apply(game_state, permanent)` implements full unearth logic: during casting from graveyard, queues `pending_unearth_choice` for human players with unearth cost; AI auto-resolves based on mana affordability
- [ ] If unearth is paid, the creature enters battlefield with haste and is marked for exile at end of turn (tracked via `unearthed_creatures: dict[str, str]` mapping perm_id -> controller)
- [ ] End-of-turn cleanup: unearthed creatures exiled at end step via SBA or turn_manager hook
- [ ] If unearthed creature leaves battlefield before end of turn, it goes to graveyard normally (not back to hand)
- [ ] Integration tests: detection, cost parsing, human choice queuing, AI auto-resolution, enters with haste, exiled at end of turn, early departure goes to graveyard

### Transmute (CR 702.98)
- [ ] `TransmuteKeyword.apply(game_state, card, player_name)` implements full transmute logic: discards the card, searches library for up to N cards with same mana cost, reveals them, puts one into hand and rest into graveyard, shuffles library
- [ ] Queues `pending_transmute_choice` for human players with matching card list; AI auto-resolves by picking highest-quality card
- [ ] Library search must be followed by shuffle (CR 400.9)
- [ ] Integration tests: detection, value parsing, discard triggers transmute, library search for same-cost cards, one to hand rest to graveyard, library shuffled

### Replicate (CR 702.63)
- [ ] `ReplicateKeyword.apply(game_state, stack_obj)` implements full replicate logic: when the spell enters the stack (or resolves), creates copies of the spell for each nonland permanent an opponent controls; may choose new targets for copies
- [ ] Queues `pending_replicate_choice` for human players with target options per copy; AI auto-resolves by targeting most valuable permanents/players
- [ ] Copies go on stack in reverse order (LIFO) so they resolve before original
- [ ] Integration tests: detection, creates correct number of copies, copies can retarget, LIFO resolution order

### Surge (CR 702.138b)
- [ ] `SurgeKeyword.apply(game_state, permanent)` implements full surge logic: during spell casting, checks if controller or teammate has cast another spell this turn; if so, queues `pending_surge_choice` with reduced cost; AI auto-resolves based on mana savings
- [ ] Surge is an alternative cost — paying it replaces the normal mana cost entirely
- [ "Spell cast this turn" tracking: use existing `spells_cast_this_turn` counter or add per-player flag
- [ ] Integration tests: detection, cost parsing, spell cast this turn enables surge, no prior spell blocks surge, human choice queuing, AI auto-resolution, alternative cost behavior

### Extort (CR 702.63b)
- [ ] `ExtortKeyword.apply(game_state, permanent)` implements full extort logic: when controller casts an instant or sorcery spell, each opponent may pay the extort cost; if they don't, controller gains 2 life and that player loses 2 life
- [ ] Queues `pending_extort_choice` for human opponents with pay/skip options; AI auto-resolves based on life total (pays if low life)
- [ ] Extort triggers from the permanent on battlefield — not from the spell being cast
- [ ] Integration tests: detection, cost parsing, triggers on instant/sorcery cast, each opponent chooses independently, gain/lose life applied correctly

### Scavenge (CR 702.138a)
- [ ] `ScavengeKeyword.apply(game_state, permanent)` implements full scavenge logic: queues `pending_scavenge_choice` for human players with cost and valid target list (creature cards in any graveyard); AI auto-resolves by exiling highest-power creature card
- [ ] If scavenge is paid, exile the target creature card from graveyard; the scavenging creature gets +N/+0 until end of turn
- [ ] +N/+0 bonus tracked via layers system or temporary P/T modification (expires at end of turn)
- [ ] Integration tests: detection, value parsing, human choice queuing, AI auto-resolution, target exiled from graveyard, +N/+0 applied to scavenger, expires at end of turn

### Counter Spell (CR 701.5)
- [ ] `CounterKeyword.apply(game_state, stack_obj)` implements full counter logic: counters the targeted spell on the stack; the spell is moved to its owner's graveyard
- [ ] Wire into stack.py's resolution flow so that when a counter spell resolves, it calls `apply_counter()` and removes the target from the stack
- [ ] Integration tests: detection, spell countered goes to graveyard, countered trigger fires (if wired), multiple targets handled

### Meld (CR 702.146b)
- [ ] `MeldKeyword.apply(game_state, card1, card2)` implements full meld logic: when both halves of a meld pair are in the graveyard, they can be put onto battlefield face down as the melded card; queues `pending_meld_choice` for human players
- [ ] Meld detection: parse pair names from oracle text (e.g., "Meld with Ashiok and Okine")
- [ ] Both cards must be in the same player's graveyard to meld
- [ ] Integration tests: detection, pair name parsing, both halves in graveyard enables meld, melded card enters battlefield, face-down state

### Cross-cutting requirements
- [ ] All `apply()` methods follow pure transform pattern: return new GameState via `model_copy(update={...})`, never mutate directly
- [ ] Full test suite passes: 2792+ regression tests, 0 failures (3 skipped + 13 xfailed expected)
- [ ] Each keyword has a dedicated integration test file in `tests/engine/test_<keyword>_integration.py` with 8-15 tests covering detection, human path, AI path, edge cases, pure transform

## Dependencies
- None (independent of other stories; uses existing casting/stack/token infrastructure)
- Unearth depends on turn_manager.py having an end-step hook for exile cleanup (minor addition)
- Replicate depends on stack copy infrastructure (may need extension to `_create_storm_copies()` pattern)

## Priority: Medium

## Estimated Effort: XL (8 keywords × ~0.5 day each = 4 days, plus tests)

## Notes
- **Unearth end-of-turn exile**: Similar to Dash's dashed_creatures tracking and Crew's crewed_vehicles tracking. Use `unearthed_creatures: dict[str, str]` on GameState mapping perm_id -> controller_name. Wire into turn_manager.py's end step for cleanup. If the creature leaves battlefield early (destroyed, sacrificed), it goes to graveyard normally — only exile at end of turn if still on battlefield.
- **Transmute library search**: Requires searching by mana cost, which means comparing `card.mana_cost` strings. The engine needs a way to find cards in library with matching CMC or exact mana cost. Reference how Scryfall's card data includes mana_cost field for comparison.
- **Replicate copy creation**: Similar to Storm's `create_storm_copies()` but the number of copies = nonland permanents opponents control (not spells cast). Each copy can have different targets. Wire into stack resolution so copies are created when the original spell resolves.
- **Surge tracking**: Need a per-player flag like `cast_spell_this_turn: bool` on PlayerState, set during casting and reset at turn start. Surge checks this flag before offering the alternative cost.
- **Extort opponent choices**: Each opponent makes an independent choice (pay or skip). This requires iterating through all opponents and queuing individual pending choices, or batching them into a single multi-choice. Reference how proliferate handles per-permanent choices for inspiration.
- **Scavenge +N/+0 tracking**: The bonus is temporary (+N/+0 until end of turn). Use the layers system (layer 7b: P/T modifications) with an effect that expires at end step, OR track via a `scavenged_bonuses: dict[str, tuple[int, int]]` field on GameState.
- **Meld complexity**: Meld requires tracking two specific cards as a pair. When both are in the graveyard, they can be melded into a third card (the back face of the MDFC). This needs special handling in zones.py for putting two cards onto battlefield simultaneously and replacing them with the melded version.
