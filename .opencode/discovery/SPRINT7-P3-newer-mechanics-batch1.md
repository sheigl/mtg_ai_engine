# Story: Newer Mechanics Batch 1 (Amass, Incubate, Forage, Explore, Connive)

## User Story
As an MTG engine developer, I want five newer set mechanics implemented as keyword modules with real `apply()` methods and integration tests, so that cards from sets after 2019 produce correct game state instead of silently no-op'ing.

## Context
Five mechanics exist in Forge but not yet in our codebase. These are non-keyword abilities (they don't have a formal keyword name) but follow consistent patterns across multiple cards:

1. **Amass** (Throne of Eldraine, 2019) — "Amass N" means "Create a number of 1/1 colorless Soldier creature tokens with haste equal to the number of +1/+1 counters you have on Soldier creatures, then put N +1/+1 counters on that Soldier." If you already control a "the army" token, just add counters instead.
2. **Incubate** (March of the Machine, 2023) — "Incubate N" means "Create an egg artifact token with 'At the beginning of your upkeep, remove a counter from this. If it has no counters, sacrifice it and create a <type> creature token.' The egg starts with N counters."
3. **Forage** (Innistrad Remastered, 2024) — "Forage" means "Discard any number of cards: Create that many Food tokens." Food is an artifact token with "{T}, Sacrifice this artifact: You gain 3 life."
4. **Explore** (Strixhaven, 2021) — "Explore" means "Draw a card, then untap all lands you control, then create a 1/1 green Frog creature token."
5. **Connive** (The Brothers' War, 2020) — "Connive {cost}" means "{cost}, Exile target nonland permanent you control until this spell resolves. If you do, draw a card."

Each needs: new module in `mtg_engine/ability/keywords/`, detection/parsing from oracle text, real `apply()` method using pure transforms, integration into stack resolution, and integration tests.

## Acceptance Criteria

### Amass (CR 702.XX)
- [ ] Create `mtg_engine/ability/keywords/amass.py` with `AmassKeyword(TriggeredKeyword)` class: detection via regex `\bamass\s+(\d+)`, parsing N value, `apply()` method
- [ ] `Amass.apply(game_state, permanent)` implements full amass logic: finds or creates "the army" 1/1 colorless Soldier creature token with haste; puts N +1/+1 counters on it; if no army exists, creates one with N counters and haste
- [ ] Army token is tracked via a new `army_tokens: dict[str, str]` field on GameState mapping player_name -> perm_id (or use existing token tracking)
- [ ] Amass only counts +1/+1 counters on Soldier creatures you control when determining if army already exists (the actual counter placement is always N new counters)
- [ ] Integration tests in `tests/engine/test_amass_integration.py`: detection, value parsing, creates army when none exists, adds to existing army, haste on new army, pure transform

### Incubate (CR 701.XX)
- [ ] Create `mtg_engine/ability/keywords/incubate.py` with `IncubateKeyword(TriggeredKeyword)` class: detection via regex `\bincubate\s+(\d+)`, parsing N value and creature type, `apply()` method
- [ ] `Incubate.apply(game_state, permanent)` implements full incubate logic: creates an Egg artifact token with N charge counters; the egg has a triggered ability that removes a counter at upkeep and hatches when last counter is removed
- [ ] Egg token metadata stores the creature type to create on hatching (e.g., "Zombie", "Dragon")
- [ ] Upkeep trigger: wire into turn_manager.py's upkeep step — for each egg with counters, remove one; if zero counters remaining, sacrifice and create the stored creature type token
- [ ] Integration tests in `tests/engine/test_incubate_integration.py`: detection, value parsing, creates egg with N counters, upkeep removes counter, hatches at 0 counters, creature type preserved

### Forage (CR 702.XX)
- [ ] Create `mtg_engine/ability/keywords/forage.py` with `ForageKeyword(TriggeredKeyword)` class: detection via regex `\bforage\b`, `apply()` method
- [ ] `Forage.apply(game_state, permanent)` implements full forage logic: queues `pending_forage_choice` for human players with hand cards list; AI auto-resolves by discarding lowest-value cards; creates N Food tokens where N = number of discarded cards
- [ ] Food token is an artifact with activated ability "{T}, Sacrifice this artifact: You gain 3 life" — stored as a Card with appropriate oracle_text and keywords
- [ ] Forage can discard 0 cards (creates 0 food) — valid but no-op choice
- [ ] Integration tests in `tests/engine/test_forage_integration.py`: detection, human choice queuing, AI auto-resolution, N discarded = N food created, zero discard valid, Food token has correct activated ability

### Explore (CR 702.XX)
- [ ] Create `mtg_engine/ability/keywords/explore.py` with `ExploreKeyword(TriggeredKeyword)` class: detection via regex `\bexplore\b`, `apply()` method
- [ ] `Explore.apply(game_state, permanent)` implements full explore logic in sequence: (1) draw a card for controller, (2) untap all lands controller controls on battlefield, (3) create a 1/1 green Frog creature token
- [ ] All three effects happen as part of the same resolution — no pending choices needed (pure deterministic effect)
- [ ] Pure transform: returns new GameState via model_copy with updated hand, battlefield (untapped lands), and frog token
- [ ] Integration tests in `tests/engine/test_explore_integration.py`: detection, draw a card, untap all lands, create frog token, sequence order correct, pure transform

### Connive (CR 702.XX)
- [ ] Create `mtg_engine/ability/keywords/connive.py` with `ConniveKeyword(CostKeyword)` class: detection via regex `\bconnive\s+(\{[^}]+\})`, parsing cost, `apply()` method
- [ ] `Connive.apply(game_state, permanent)` implements full connive logic: queues `pending_connive_choice` for human players with cost and valid target list (nonland permanents controller controls); AI auto-resolves by exiling lowest-value nonland permanent if mana is affordable
- [ ] Exiled permanent returns to battlefield when the spell resolves (tracked via ExileStack with reason="connive" and return_on_resolve=True)
- [ ] If connive cost is paid, controller draws a card as part of the spell resolution
- [ ] Integration tests in `tests/engine/test_connive_integration.py`: detection, cost parsing, human choice queuing, AI auto-resolution, exile target until resolve, draw a card on payment, permanent returns after resolution

### Cross-cutting requirements
- [ ] All new modules follow established patterns: class hierarchy from base.py (TriggeredKeyword or CostKeyword), detection/parsing via regex, `apply()` method using pure transforms (`model_copy(update={...})`)
- [ ] Full test suite passes: 2792+ regression tests, 0 failures (3 skipped + 13 xfailed expected)
- [ ] Each keyword has a dedicated integration test file in `tests/engine/test_<keyword>_integration.py` with 8-15 tests covering detection, human path, AI path, edge cases, pure transform

## Dependencies
- None (independent of other Sprint 7 stories; uses existing token creation and stack infrastructure)
- Incubate depends on turn_manager.py upkeep step having a hook for egg counter removal (minor addition)

## Priority: Medium

## Estimated Effort: L (5 mechanics × ~0.6 day each = 3 days)

## Notes
- **Amass army tracking**: The "army" token is a special case — it's always named "the army" and there can only be one per player. Use a dedicated field like `army_token_id: Optional[str]` on GameState (keyed by controller) to track which perm_id is the current army. When amass resolves, check this first before creating a new token.
- **Incubate egg lifecycle**: Eggs are artifact tokens with charge counters and a built-in triggered ability. The upkeep trigger needs to be wired into turn_manager.py's existing upkeep flow (similar to how Suspend time counter removal works). Consider adding an `_check_egg_upkeep(gs)` function called from the same place as suspend upkeep.
- **Forage Food token**: Food is a well-defined token type in MTG. Create it as a Card with `type_line="Artifact — Food"`, `oracle_text="{T}, Sacrifice this artifact: You gain 3 life."`, and appropriate keywords. The activated ability can be resolved through the existing stack effect resolution pipeline (gain life pattern already exists).
- **Explore sequence order**: CR specifies draw first, then untap, then create token. This matters because some cards trigger on "whenever you draw a card" — those triggers go on the stack before untap and token creation happen. Ensure the three effects are applied sequentially within `apply()`.
- **Connive exile return**: The exiled permanent needs to return when the spell resolves, not immediately. Use an ExileStack entry with metadata tracking which perm_id to return and to whose control. Wire into stack resolution so that when the conniving spell finishes resolving, it checks for matching ExileStack entries and returns those permanents.
