# Story: Newer Mechanics Batch 2 (Goad, Detain, Heist/Protect, Battle/Siege, Intensify)

## User Story
As an MTG engine developer, I want five newer combat-modifier and interactive mechanics implemented as keyword modules with real `apply()` methods and integration tests, so that cards from sets after 2019 produce correct game state instead of silently no-op'ing.

## Context
Five more mechanics exist in Forge but not yet in our codebase:

1. **Goad** (Theros Beyond Death, 2021) — "Goad creatures you don't control until end of turn" means those creatures must attack each turn if able, and they can't attack the player who goaded them.
2. **Detain** (The Brothers' War, 2020) — "Detain target creature until end of turn" means that creature can't attack or block with flying creatures this turn.
3. **Heist/Protect** (Phyrexia All Will Be One, 2022) — Heist: "When you buy this artifact from the sideboard, put it onto the battlefield attached to target non-Sorcerer creature an opponent controls." Protect: "Whenever this creature becomes blocked, if it's not blocking a creature with protect, return this Equipment to its owner's hand."
4. **Battle/Siege** (Kaldheim, 2021) — Two-sided MDFC mechanic. Siege side is an enchantment that can be upgraded by putting power counters on it. When it has enough counters, you may transform it into the Battle creature side.
5. **Intensify** (The Lost Caverns of Ixalan, 2023) — "Intensify {hybrid cost}" is a hybrid kicker: pay any combination of colors in the hybrid cost to kick the spell.

Each needs: new module in `mtg_engine/ability/keywords/`, detection/parsing from oracle text, real `apply()` method using pure transforms, integration into combat/casting flow, and integration tests.

## Acceptance Criteria

### Goad (CR 702.XX)
- [ ] Create `mtg_engine/ability/keywords/goad.py` with `GoadKeyword(TriggeredKeyword)` class: detection via regex `\bgoad\b`, `apply()` method
- [ ] `Goad.apply(game_state, permanent, target)` implements full goad logic: marks the targeted creature(s) as "goaded" until end of turn; goaded creatures must attack each combat if able and can't attack the player who applied goad
- [ ] Goad tracking: use a new `goaded_creatures: dict[str, list[str]]` field on GameState mapping goading_player -> [perm_ids], cleared at end step
- [ ] Combat declaration hook: in `combat/core.py`'s `declare_attackers()`, validate that goaded creatures are attacking and not attacking their goader
- [ ] Integration tests in `tests/engine/test_goad_integration.py`: detection, applies goad marker, goaded creature must attack, can't attack goader, expires at end of turn

### Detain (CR 702.XX)
- [ ] Create `mtg_engine/ability/keywords/detain.py` with `DetainKeyword(TriggeredKeyword)` class: detection via regex `\bdetain\b`, `apply()` method
- [ ] `Detain.apply(game_state, permanent, target)` implements full detain logic: marks the targeted creature as "detained" until end of turn; detained creatures can't attack and can't block flying creatures
- [ ] Detain tracking: use a new `detained_creatures: list[str]` field on GameState with perm_ids, cleared at end step
- [ ] Combat hooks: in `combat/core.py`, validate that detained creatures can't be declared as attackers; in blocker assignment, validate that detained creatures can't block flying attackers
- [ ] Integration tests in `tests/engine/test_detain_integration.py`: detection, applies detain marker, detained creature can't attack, can't block flying, CAN block non-flying, expires at end of turn

### Heist/Protect (CR 702.XX)
- [ ] Create `mtg_engine/ability/keywords/heist.py` with `HeistKeyword(TriggeredKeyword)` class: detection via regex `\bheist\b`, `apply()` method for the buy-from-sideboard + attach logic
- [ ] Create `mtg_engine/ability/keywords/protect_keyword.py` (distinct from hexproof/shroud protect) with `ProtectKeyword(PassiveKeyword)` class: detection via oracle text patterns, query helpers for blocking validation
- [ ] Heist: when triggered, moves artifact from sideboard to battlefield attached to target opponent's creature; queues `pending_heist_choice` for human players with valid target list
- [ ] Protect (on Equipment): whenever the equipped creature becomes blocked, if it's not blocking a creature with protect keyword, return this equipment to its owner's hand
- [ ] Integration tests in `tests/engine/test_heist_integration.py`: detection, sideboard -> battlefield attach, human choice queuing, AI auto-resolution, protect returns on block without protected blocker

### Battle/Siege (CR 702.XX)
- [ ] Create `mtg_engine/ability/keywords/battle_siege.py` with `BattleSiegeKeyword(TriggeredKeyword)` class: detection via regex patterns for "put a power counter" and transform threshold, `apply()` method
- [ ] Siege side: enchantment that enters with 0 power counters; can be activated to put N power counters on it (cost varies by card)
- [ ] Transform trigger: when the siege has enough power counters (threshold parsed from oracle text), player may transform it into the Battle creature side
- [ ] Wire into existing MDFC transform infrastructure in zones.py's `_transform_mdfc()` — battle/siege uses the same flip mechanism as other MDFCs
- [ ] Integration tests in `tests/engine/test_battle_siege_integration.py`: detection, siege enters with 0 counters, power counter activation, transform threshold check, transforms to Battle side

### Intensify (CR 702.XX)
- [ ] Create `mtg_engine/ability/keywords/intensify.py` with `IntensifyKeyword(CostKeyword)` class: detection via regex `\bintensify\s+(\{[^}]+\})`, parsing hybrid cost, `apply()` method
- [ ] `Intensify.apply(game_state, permanent)` implements full intensify logic: queues `pending_intensify_choice` for human players with hybrid cost; AI auto-resolves based on mana affordability using flexible color matching
- [ ] Hybrid cost payment: unlike regular kicker (exact colors), intensify allows paying any combination of the colors in the hybrid cost. E.g., `{2}{W/U}{U/W}` can be paid as {2WW}, {2UU}, {2WU}, etc.
- [ ] If intensify is paid, the spell resolves with enhanced effects (intensified=True metadata on stack object)
- [ ] Integration tests in `tests/engine/test_intensify_integration.py`: detection, hybrid cost parsing, human choice queuing, AI auto-resolution, flexible color payment, all valid combinations accepted

### Cross-cutting requirements
- [ ] All new modules follow established patterns: class hierarchy from base.py (TriggeredKeyword, CostKeyword, or PassiveKeyword), detection/parsing via regex, `apply()` method using pure transforms (`model_copy(update={...})`)
- [ ] Full test suite passes: 2792+ regression tests, 0 failures (3 skipped + 13 xfailed expected)
- [ ] Each keyword has a dedicated integration test file in `tests/engine/test_<keyword>_integration.py` with 8-15 tests covering detection, human path, AI path, edge cases, pure transform

## Dependencies
- None (independent of other Sprint 7 stories; uses existing combat/casting/token infrastructure)
- Goad/Detain depend on combat/core.py having hooks for attack/block restrictions (minor additions to existing validation flow)
- Battle/Siege depends on existing MDFC transform infrastructure in zones.py

## Priority: Low

## Estimated Effort: L (5 mechanics × ~0.6 day each = 3 days)

## Notes
- **Goad combat enforcement**: Goad requires two checks during declare attackers: (1) goaded creatures MUST attack if able, and (2) they can't attack the player who goaded them. The first is a "must" constraint (like trample damage assignment), the second is a targeting restriction. Reference how combat declaration validation works in `combat/core.py`'s `declare_attackers()`.
- **Detain flying blocker restriction**: Detained creatures CAN block non-flying creatures — only flying blockers are prevented. This requires checking the attacker's keywords during blocker assignment. Reference how Reach allows blocking flying (in `reach.py`) for the inverse pattern.
- **Heist sideboard interaction**: Heist moves cards from sideboard to battlefield, which is unusual. The engine currently doesn't have a "buy from sideboard" flow — this needs a new path in zones.py or a dedicated heist resolution function that handles sideboard -> battlefield + attach in one atomic operation.
- **Protect (Equipment) vs Protect (keyword)**: Don't confuse Phyrexia's "protect" on Equipment with the traditional protect keyword (which combines fortify, ward, shroud, etc.). The Phyrexia version is simpler: just returns to hand if blocking a creature without protect. Implement as a separate module from any future full protect keyword.
- **Battle/Siege transform threshold**: Each battle/siege card has its own counter threshold (e.g., "When this has 5 power counters, you may transform it"). Parse the threshold from oracle text using regex like `when this has (\d+) power counters`. Wire into the existing MDFC transform flow so the Battle side enters correctly.
- **Intensify hybrid cost parsing**: Hybrid costs like `{W/U}` need special handling — they represent "either W or U". The payment validation should accept any valid combination of colors from all hybrid symbols in the cost. Reference how Scryfall represents hybrid mana costs and adapt `parse_mana_cost()` in `engine/mana.py` to handle hybrid symbols.
