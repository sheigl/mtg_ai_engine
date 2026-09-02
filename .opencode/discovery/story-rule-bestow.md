# Story: Bestow (CR 702.69)

## User Story
As a game engine developer, I want the Bestow mechanic to function correctly, so that bestow cards can be cast as auras with bestow cost or as creatures at sorcery speed per CR 702.69.

## Context
Bestow is an alternative cost ability. A card with bestow can be cast either as a creature spell (paying its mana cost) or as an Aura spell (paying its bestow cost) that enchants a creature. While bestowed, it's not a creature. If the enchanted creature leaves the battlefield, the bestowed card "falls off" and becomes a creature again.

### Comprehensive Rules Grounding
- **CR 702.69a**: "Bestow represents two static abilities and one triggered ability. 'Bestow [cost]' means you may cast this card as an Aura spell with enchant creature by paying [cost] rather than its mana cost."
- **CR 702.69b**: "If the enchanted creature leaves the battlefield, the bestowed card becomes a creature again."
- **CR 702.69c**: "Bestow is an alternative cost that can be paid rather than the card's mana cost."
- **Example card**: Boon Satyr — "Bestow {3}{G}{G}" — can be cast as a creature or as an Aura

## Acceptance Criteria
- [ ] Bestow cost detection: `parse_bestow_cost(oracle_text) -> str | None` parses bestow cost from oracle
- [ ] Alternative cost: casting for bestow cost makes it an Aura spell (type change)
- [ ] When cast with bestow: spell has type "Enchantment — Aura" and targets a creature
- [ ] When bestowed permanent is on battlefield: it's NOT a creature, it's an Aura attached to target creature
- [ ] When enchanted creature leaves battlefield: bestow permanent becomes a creature again (falls off)
- [ ] While bestowed: it grants abilities/P/T as specified in the card's text
- [ ] Bestow vs. creature mode: different casting costs, different types, different targeting requirements
- [ ] For human players: engine presents both casting options (normal cast vs. bestow)
- [ ] For AI players: heuristic to choose bestow vs. creature mode based on board state
- [ ] Pure transform: bestow resolution returns new GameState via `model_copy(update={...})`
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- This is a rule-level wrapper for the existing keyword story `story-kw-bestow.md`

## Priority: Medium

## Status: ❌ Not Implemented

### Gap Description
Bestow keyword is recognized in the ability parser keyword list but has zero implementation anywhere in the engine. There is no parse_bestow_cost() function, no alternative cost mechanism for bestow, no Aura-vs-creature casting mode, no 'fall off and become creature' logic, and no bestow keyword module.

## Estimated Effort: M

## Notes
- **This story is a rule-level companion to `story-kw-bestow.md`** — the keyword story covers the module implementation, while this story covers the CR 702.69 rules grounding
- Bestow is from Theros block and has been heavily featured in mechanics
- Key rules interaction: when the enchanted creature dies, the bestow permanent enters the battlefield as a creature — it triggered "dies" of the creature, and the bestow permanent is a new object on the battlefield
- When bestow permanent falls off, it doesn't "enter the battlefield" — it was already there as an Aura, it just changes state to become a creature
- Bestow targeting: targets only creatures (since it becomes an Aura with "enchant creature")
