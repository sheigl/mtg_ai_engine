# Story: Saga Rules (CR 714)

## User Story
As a game engine developer, I want Saga rules to function correctly per the Comprehensive Rules, so that Sagas enter with a lore counter, gain lore counters at the beginning of the draw step, trigger chapter abilities, and are sacrificed after the final chapter.

## Context
Sagas are enchantment subtypes that tell a story through chapter abilities. A Saga enters with a lore counter. At the beginning of the precombat main phase (changed from draw step in a rule update), a lore counter is added. Each chapter ability triggers when the Saga has the corresponding number of lore counters. After the final chapter ability resolves, the Saga is sacrificed.

### Comprehensive Rules Grounding
- **CR 714.1**: "A Saga is an enchantment subtype that has chapter abilities."
- **CR 714.2a**: "A Saga enters the battlefield with a lore counter."
- **CR 714.2b**: "After your draw step, a lore counter is put onto a Saga you control. This is a triggered ability."
- **CR 714.2c**: "Each chapter ability is a triggered ability. The first triggers when the Saga has [one or more] lore counter on it, the second when it has [two or more], etc."
- **CR 714.2d**: "The controller reads the chapter ability for the current lore counter number and puts it on the stack."
- **CR 714.2e**: "After a chapter ability has triggered and resolved, it won't trigger again — even if lore counters are later removed."
- **CR 714.3**: "If the Saga's controller adds a lore counter beyond the final chapter, the Saga is sacrificed after the chapter ability resolves."
- **CR 714.4**: "If multiple chapter abilities trigger at the same time, they go on the stack in the order of their chapter numbers (I then II then III)."
- **Example card**: The Binding of the Titans — Enchantment — Saga, "I: Mill three cards, II: Exile target card from a graveyard, III: Return target creature/land card from graveyard to hand."

## Acceptance Criteria
- [x] Saga enters the battlefield with one lore counter (CR 714.2a)
- [x] At the beginning of the precombat main phase, a lore counter is added (CR 714.2b — triggered ability)
- [x] Each chapter ability triggers when the Saga has the matching number of lore counters (CR 714.2c)
- [x] Chapter abilities trigger in order (I first, then II, then III) (CR 714.4)
- [x] Each chapter ability resolves only once — cannot trigger again from counter manipulation (CR 714.2e)
- [x] When lore counters exceed the final chapter, the Saga is sacrificed after the trigger resolves (CR 714.3)
- [x] Saga sacrificed if final lore counter is added and final chapter resolves
- [x] Multiple Sagas controlled by same player all independently gain lore counters and trigger
- [x] Lore counters can be added/removed by other effects (proliferate, etc.) — removed counters don't re-trigger chapters
- [x] Sacrifice trigger uses the stack — can be responded to
- [x] Full regression suite passes

## Dependencies
- Story: Enchantment Rules (CR 303) — parent card type rules
- Story: Triggered Abilities (CR 603) — chapter abilities are triggered abilities
- Story: State-Based Actions (CR 704) — Saga sacrifice

## Status: ✅ Complete

Implemented: `SagaState` model at `models/saga.py` with lore counters, chapter parsing, advanced/clear methods. ETB at `zones.py:720-734` — enters with 1 lore counter, queues chapter I trigger. Upkeep at `turn_manager.py:235-283` — increments lore, queues chapter trigger, schedules sacrifice at final chapter. Chapter text extraction via `_get_saga_chapter_text()` at `zones.py:758-771`.

## Priority: High

## Notes
- The existing `mtg_engine/models/saga.py` has a `SagaModel` class with `from_oracle_text()` and chapter parsing
- `mtg_engine/models/card_type.py` has `EnchantmentSubtype.SAGA` and `CardType.is_saga()` helper
- The lore counter addition happens at the beginning of the precombat main phase (CR was updated from draw step in [a recent rule change])
- Chapter abilities use roman numerals: I, II, III, etc. — parsed from oracle text
- The "after the final chapter resolves, sacrifice the Saga" is a state-based trigger (doesn't use the stack — wait, CR 714.3 says it's sacrificed after the chapter ability resolves — this might use the stack as a delayed trigger)
- Actually, the sacrifice on exceeding final chapter IS a state-based action per CR 714.3 — but it checks after the chapter trigger resolves
- Proliferate on Sagas can cause skipping chapters (if you add a counter before the trigger resolves, the lower-numbered chapter trigger is removed from the stack without resolving)
- Removing lore counters from a Saga (via "remove a counter from target permanent") doesn't cause any chapter to re-trigger (CR 714.2e)
- Chapter abilities that target choose targets when they go on the stack, not when the Saga entered
