# Story: Prototype (CR 702.XX — The Brothers' War)

## User Story
As an MTG engine developer, I want a new prototype keyword module with real apply() and integration tests, so that cards with prototype {cost} work correctly in the engine.

## Context
No file exists for prototype. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.XX**: "Prototype is an alternative cost. 'Prototype [cost] — [power/toughness]' means 'You may cast this spell by paying [cost] rather than its mana cost. If you do, it enters with base power and toughness [power/toughness] and base mana cost [cost].'"
- **Example card**: Prototype Portal — "Prototype {1}{W} — 2/2 (You may cast this spell for {1}{W}. If you do, it enters with 2/2 and is white.)"
- **Rule source**: Alternative cost that changes P/T, mana cost, and color

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/prototype.py` with `Prototype` class extending `CostKeyword`
- [ ] `parse_prototype(oracle_text) -> tuple[str, str, int, int] | None` detects prototype cost, P/T, and color
- [ ] `apply()` modifies spell characteristics when cast for prototype cost: changes P/T, mana cost, color
- [ ] The creature retains its original types and abilities when prototyped
- [ ] Only power, toughness, mana cost, and color change — not card type, creature types, or abilities
- [ ] For human players: queues `pending_prototype_choice`
- [ ] For AI players: auto-resolves (prefers prototype if affordable at sorcery speed)
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: cast for prototype cost (smaller P/T), cast normally, prototype changes color, prototype changes mana cost, prototype keeps abilities and types, human choice queuing, AI auto-resolution
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: L

## Notes
- The Brothers' War mechanic
- Prototype permanently modifies the card's characteristics (not an effect that can end)
- The card has a different mana value (and color) while on the stack and battlefield when prototyped
- In other zones, the card uses its normal characteristics
- Very few cards have prototype (mostly the Mishra's Warforms cycle)
