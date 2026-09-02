# Story: Common Modern Mechanics — Amass, Explore, Goad, Detain

## User Story
As an MTG engine developer, I want four common modern mechanics implemented as keyword modules with real `apply()` methods and integration tests, so that cards from sets 2019-2025 produce correct game state instead of silently no-op'ing.

## Context
Four more missing keywords are high-frequency in modern MTG:

1. **Amass** (Throne of Eldraine, 2019) — "Amass N" means "Create a number of 1/1 colorless Soldier creature tokens with haste equal to the number of +1/+1 counters you have on Soldier creatures, then put N +1/+1 counters on that Soldier." If you already control an army token, just add counters.

2. **Explore** (Strixhaven, 2021) — "Explore" means "Draw a card, then untap all lands you control, then create a 1/1 green Frog creature token." Three sequential effects in one action.

3. **Goad** (Theros Beyond Death, 2021) — "Goad target creature until end of turn" means that creature must attack each combat if able and can't attack the player who goaded it.

4. **Detain** (The Brothers' War, 2020) — "Detain target creature until end of turn" means that creature can't attack or block with flying creatures this turn.

## Acceptance Criteria

### Amass
- [ ] Create `mtg_engine/ability/keywords/amass.py` with `AmassKeyword(TriggeredKeyword)` class: detection via regex `\bamass\s+(\d+)`, parsing N value, `apply()` method
- [ ] `Amass.apply(game_state, permanent)` implements full amass logic: finds or creates "the army" 1/1 colorless Soldier creature token with haste; puts N +1/+1 counters on it; if no army exists, creates one with N counters and haste
- [ ] Army token tracking: use `army_tokens: dict[str, str]` field on GameState mapping player_name -> perm_id (or use existing token tracking with name="the army")
- [ ] Pure transform: returns new GameState via model_copy with updated army token
- [ ] Integration tests in `tests/engine/test_amass_integration.py`: detection, value parsing, creates army when none exists, adds to existing army, haste on new army, pure transform

### Explore
- [ ] Create `mtg_engine/ability/keywords/explore.py` with `ExploreKeyword(TriggeredKeyword)` class: detection via regex `\bexplore\b`, `apply()` method
- [ ] `Explore.apply(game_state, permanent)` implements full explore logic in sequence: (1) draw a card for controller, (2) untap all lands controller controls on battlefield, (3) create a 1/1 green Frog creature token
- [ ] All three effects happen as part of the same resolution — no pending choices needed (pure deterministic effect)
- [ ] Pure transform: returns new GameState via model_copy with updated hand, battlefield (untapped lands), and frog token
- [ ] Integration tests in `tests/engine/test_explore_integration.py`: detection, draw a card, untap all lands, create frog token, sequence order correct, pure transform

### Goad
- [ ] Create `mtg_engine/ability/keywords/goad.py` with `GoadKeyword(TriggeredKeyword)` class: detection via regex `\bgoad\b`, `apply()` method
- [ ] `Goad.apply(game_state, permanent, target)` implements full goad logic: marks the targeted creature(s) as "goaded" until end of turn; goaded creatures must attack each combat if able and can't attack the player who applied goad
- [ ] Goad tracking: use `goaded_creatures: dict[str, list[str]]` field on GameState mapping goading_player -> [perm_ids], cleared at end step
- [ ] Combat declaration hook: in `combat/core.py`'s `declare_attackers()`, validate that goaded creatures are attacking and not attacking their goader
- [ ] Queues `pending_goad_choice` for human players with valid target list; AI auto-resolves by targeting opponent's highest-power creature
- [ ] Integration tests in `tests/engine/test_goad_integration.py`: detection, applies goad marker, goaded creature must attack, can't attack goader, expires at end of turn

### Detain
- [ ] Create `mtg_engine/ability/keywords/detain.py` with `DetainKeyword(TriggeredKeyword)` class: detection via regex `\bdetain\b`, `apply()` method
- [ ] `Detain.apply(game_state, permanent, target)` implements full detain logic: marks the targeted creature as "detained" until end of turn; detained creatures can't attack and can't block flying creatures
- [ ] Detain tracking: use `detained_creatures: list[str]` field on GameState with perm_ids, cleared at end step
- [ ] Combat hooks: in `combat/core.py`, validate that detained creatures can't be declared as attackers; in blocker assignment, validate that detained creatures can't block flying attackers
- [ ] Queues `pending_detain_choice` for human players with valid target list; AI auto-resolves by targeting opponent's most threatening creature
- [ ] Integration tests in `tests/engine/test_detain_integration.py`: detection, applies detain marker, detained creature can't attack, can't block flying, CAN block non-flying, expires at end of turn

### Cross-cutting requirements
- [ ] All new modules follow established patterns: class hierarchy from base.py (TriggeredKeyword or CostKeyword), detection/parsing via regex, `apply()` method using pure transforms (`model_copy(update={...})`)
- [ ] Full test suite passes: 2792+ regression tests, 0 failures (3 skipped + 13 xfailed expected)
- [ ] Each keyword has a dedicated integration test file in `tests/engine/test_<keyword>_integration.py` with 8-15 tests covering detection, human path, AI path, edge cases, pure transform

## Dependencies
- None (independent of other stories; uses existing token creation and combat infrastructure)
- Goad/Detain depend on combat/core.py having hooks for attack/block restrictions (minor additions to existing validation flow)

## Priority: Medium

## Estimated Effort: L (4 keywords × ~0.6 day each = 2.5 days, plus tests)

## Notes
- **Amass army tracking**: The "army" token is a special case — it's always named "the army" and there can only be one per player. Use a dedicated field like `army_token_id: Optional[str]` on GameState (keyed by controller) to track which perm_id is the current army. When amass resolves, check this first before creating a new token.
- **Explore sequence order**: CR specifies draw first, then untap, then create token. This matters because some cards trigger on "whenever you draw a card" — those triggers go on the stack before untap and token creation happen. Ensure the three effects are applied sequentially within `apply()`.
- **Goad combat enforcement**: Goad requires two checks during declare attackers: (1) goaded creatures MUST attack if able, and (2) they can't attack the player who goaded them. The first is a "must" constraint (like trample damage assignment), the second is a targeting restriction. Reference how combat declaration validation works in `combat/core.py`'s `declare_attackers()`.
- **Detain flying blocker restriction**: Detained creatures CAN block non-flying creatures — only flying blockers are prevented. This requires checking the attacker's keywords during blocker assignment. Reference how Reach allows blocking flying (in `reach.py`) for the inverse pattern.
