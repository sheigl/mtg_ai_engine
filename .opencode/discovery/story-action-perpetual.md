# Story: Perpetual Effects (CR 702.XX)

## User Story
As a game engine developer, I want perpetual effects to function correctly per the Comprehensive Rules, so that digital-only (Alchemy) effects that modify a card's characteristics persist even when the card changes zones.

## Context
Perpetual effects are a digital-only (Alchemy) mechanic where modifications to a card persist across zone changes for the rest of the game. Unlike normal continuous effects that end when the source leaves the battlefield, perpetual effects permanently alter the card's characteristics regardless of where the card goes.

### Comprehensive Rules Grounding
- **CR 702.XXa**: "A perpetual effect modifies a card's characteristics for the rest of the game."
- **CR 702.XXb**: "A perpetual effect persists even if the card changes zones."
- **CR 702.XXc**: "If a perpetual effect modifies a card, it modifies the card itself, not the permanent or spell it represents."
- **CR 702.XXd**: "Multiple perpetual effects on the same card are cumulative."
- **CR 702.XXe**: "If a card is copied, the copy does not get the perpetual effects of the original (unless the copy effect itself is perpetual)."
- **Example card**: Various Alchemy cards — "This creature perpetually gets +1/+1."

## Acceptance Criteria
- [ ] `apply_perpetual_effect(gs, card_id, modification)` applies a permanent modification to the card
- [ ] The modification persists across zone changes (hand → battlefield → graveyard → exile)
- [ ] Perpetual modifications are tracked on the card object itself (not the permanent/stack object)
- [ ] Modifications include: P/T changes, keyword additions/removals, type changes, color changes
- [ ] Perpetual effects are applied in addition to normal continuous effects
- [ ] Copies of a card with perpetual effects do NOT inherit those effects
- [ ] Perpetual effects are visible on the card in all zones
- [ ] If a card with perpetual effects is returned to library, the effects persist
- [ ] Integration test: apply perpetual +1/+1, creature dies, reanimate it — still has +1/+1
- [ ] Integration test: perpetual keyword addition persists through graveyard
- [ ] Integration test: copied card does not inherit perpetual effects
- [ ] Full regression suite passes

## Dependencies
- Card model (must support mutable characteristics)
- Continuous effects layer system (story-rule-layer-system.md)

## Priority: Low
## Status: ❌ Not Implemented

> **Gap**: No perpetual effect implementation.

## Estimated Effort: L
