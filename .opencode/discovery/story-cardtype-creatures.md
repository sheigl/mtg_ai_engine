# Story: Creature Rules (CR 302)

## User Story
As a game engine developer, I want creature rules to function correctly per the Comprehensive Rules, so that creatures can attack, block, deal combat damage, and interact with summoning sickness and creature types properly.

## Context
Creatures are the primary permanent type for attacking and blocking. They have power and toughness, are subject to summoning sickness (cannot attack or use tap abilities unless they have haste), and have creature types (subtypes like Beast, Goblin, Human). Creatures can also have other types (Artifact Creature, Enchantment Creature, etc.).

### Comprehensive Rules Grounding
- **CR 302.1**: "A creature is a permanent that can attack and block."
- **CR 302.2**: "A creature's power and toughness are displayed as a fraction; power is on top. A creature with 0 or less power deals no combat damage."
- **CR 302.3**: "A creature entering the battlefield triggers 'enters the battlefield' abilities."
- **CR 302.4**: "A creature's creature type is determined by its subtype line, e.g., 'Creature — Goblin Wizard' has types Goblin and Wizard."
- **CR 302.5**: "A creature's controller may assign combat damage equal to its power during the combat damage step."
- **CR 302.6**: "A creature that hasn't been under its controller's control continuously since the beginning of their most recent turn can't attack or use activated abilities with the tap symbol {T} or the untap symbol {Q}. This is known as summoning sickness."
- **Example card**: Grizzly Bears — 2/2 Creature — Bear, power 2, toughness 2

## Acceptance Criteria
- [x] Creature permanents have `power` and `toughness` fields used for combat damage calculation
- [x] Summoning sickness prevents creatures from attacking and using {T}/{Q} abilities unless they have haste (CR 302.6)
- [x] Creatures with 0 or less power deal 0 combat damage (CR 302.2)
- [x] Creature entering the battlefield triggers "enters the battlefield" triggers (CR 302.3)
- [x] Creature types parsed from type_line subtypes and trackable per permanent
- [x] Creature death triggers the normal SBA + trigger flow
- [x] Hybrid card types (Artifact Creature, Enchantment Creature, etc.) handled correctly
- [x] Creature with 0 or less toughness is put into graveyard by SBA (CR 704.5f)
- [x] Creature with lethal damage (toughness <= damage) is destroyed by SBA (CR 704.5h)
- [x] Full regression suite passes

## Dependencies
- Story: State-Based Actions (CR 704) — creature death via SBA
- Story: Combat System (CR 506-511) — attacking and blocking

## Status: ✅ Complete

Implemented: `Permanent.summoning_sick` at `models/game.py:107`, cleared at turn start (`turn_manager.py:134`), enforced in combat (`combat/core.py:251-257`). Full power/toughness system with bonuses (`game.py:113-114`). Combat damage engine (`combat/core.py`). SBA lethal damage (`sba.py:130-168`). Deathtouch support (`keywords/deathtouch.py`). Haste removes summoning sickness (`stack.py:599`).

## Priority: High
