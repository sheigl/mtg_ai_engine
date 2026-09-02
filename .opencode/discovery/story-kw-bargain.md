# Story: Bargain (CR 702.XX — Wilds of Eldraine)

## User Story
As an MTG engine developer, I want a new bargain keyword module with real apply() and integration tests, so that cards with bargain work correctly in the engine.

## Context
No file exists for bargain. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.XX**: "Bargain is an optional additional cost. 'Bargain' means 'You may sacrifice an artifact, enchantment, or token as you cast this spell.' A spell cast with its bargain cost paid has the indicated additional effect."
- **Example card**: Bargain (keyword) — "Bargain (You may sacrifice an artifact, enchantment, or token as you cast this spell. If you do, [additional effect].)"
- **Rule source**: Optional additional cost that provides an enhanced effect

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/bargain.py` with `Bargain` class extending `CostKeyword`
- [ ] `detect_bargain(oracle_text) -> bool` detects bargain keyword
- [ ] `apply()` checks for eligible permanents to sacrifice (artifact, enchantment, or token)
- [ ] For human players: queues `pending_bargain_choice` with eligible permanent options
- [ ] For AI players: auto-resolves (sacrifices the least valuable eligible permanent, or skips if none)
- [ ] When bargained, the spell's resolution path includes the bonus effect
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: basic bargain with artifact, bargain with enchantment, bargain with token, no eligible permanents (can't bargain), non-bargain cast same spell, human choice queuing, AI auto-resolution, the bonus effect resolves correctly
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: S

## Notes
- Wilds of Eldraine mechanic
- The bonus effect is typically "draw a card" or a stronger version of the base effect
- The bargain choice is made during casting (part of determining total cost)
- Similar pattern to kicker or casualty but the cost is always "sacrifice an artifact, enchantment, or token"
- If you can't sacrifice anything (no eligible permanents), you can still cast the spell without the bonus
