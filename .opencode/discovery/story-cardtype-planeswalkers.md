# Story: Planeswalker Rules (CR 306)

## User Story
As a game engine developer, I want planeswalker rules to function correctly per the Comprehensive Rules, so that planeswalkers enter with loyalty counters, use loyalty abilities once per turn, can be attacked, and the planeswalker uniqueness rule (merged with legend rule) functions correctly.

## Context
Planeswalkers are powerful permanents with loyalty counters and loyalty abilities. They have a starting loyalty value printed in the bottom-right corner of the card. Planeswalkers can be attacked by opponents' creatures (and creatures can be redirected to planeswalkers). Each planeswalker can be targeted by one loyalty ability per turn. The "planeswalker uniqueness rule" was removed with the release of Dominaria (2018); planeswalkers now use the standard legend rule.

### Comprehensive Rules Grounding
- **CR 306.1**: "A planeswalker is a permanent with loyalty abilities and loyalty counters."
- **CR 306.2**: "A planeswalker enters the battlefield with loyalty counters equal to its printed loyalty number."
- **CR 306.3**: "A non-zero loyalty ability on a planeswalker may be activated once per turn, and only as a sorcery."
- **CR 306.4**: "Planeswalker abilities are loyalty abilities if they have a cost of +N, -N, or 0, and they specify the change in loyalty."
- **CR 306.5**: "A planeswalker can be attacked. Creature damage directed at a planeswalker reduces its loyalty counters."
- **CR 306.6**: "If a planeswalker has 0 loyalty, it is put into its owner's graveyard as a state-based action."
- **CR 306.7**: "Planeswalkers are subject to the legend rule (CR 704.5j) — two planeswalkers with the same name controlled by the same player result in one being put into the graveyard."
- **CR 306.8**: "Damage dealt to a player may be redirected to a planeswalker they control by the source's controller."
- **Example card**: Jace, the Mind Sculptor — "{+2: Look at top 5...}, {0: Draw 3...,}, {-1: Return target...}, {-12: Exile all..."}

## Acceptance Criteria
- [ ] Planeswalkers enter the battlefield with loyalty counters equal to printed loyalty (CR 306.2)
- [ ] Loyalty abilities can be activated once per turn, only as a sorcery (CR 306.3)
- [ ] Loyalty cost (+N/−N/0) is paid by adding/removing loyalty counters from the planeswalker
- [ ] Planeswalker loyalty abilities use the stack (they are activated abilities, not mana abilities)
- [ ] A planeswalker with 0 loyalty is put into graveyard as an SBA (CR 306.6)
- [ ] Planeswalkers can be attacked — creatures can attack planeswalkers directly (CR 306.5)
- [ ] Planeswalkers follow the legend rule (same name → one is sacrificed) (CR 306.7, 704.5j)
- [ ] Combat damage to planeswalkers removes loyalty counters rather than reducing life
- [ ] Non-combat damage to planeswalkers removes loyalty counters
- [ ] Redirection of damage from player to planeswalker (CR 306.8) — replacement effect
- [ ] Full regression suite passes

## Dependencies
- Story: Loyalty Abilities (CR 606) — detailed loyalty ability framework
- Story: Legend Rule (CR 704.5j) — planeswalker uniqueness
- Story: State-Based Actions (CR 704) — 0 loyalty SBA

## Status: 🔄 Partial

Implemented: `Permanent.loyalty` field, SBA for 0 loyalty (`sba.py:207-215`), combat damage reduces loyalty (`combat/core.py:634-639`), `loyalty_activated_this_turn` reset at untap (`turn_manager.py:135`). Loyalty ability system: `ability/loyalty.py` (285 lines) with tracker, activation validation, effect execution. API endpoint for loyalty activation.

**Gap**: `_execute_loyalty_effect()` uses simplified direct effect resolution for basic patterns (draw, damage, token) instead of routing through the full stack system. Works for common cases but not comprehensive for complex loyalty abilities.

## Priority: High

## Notes
- The Card model has a `loyalty: Optional[str]` field for printed loyalty (e.g., "3" for Jace)
- Planeswalker subtypes (e.g., "Jace", "Liliana", "Chandra") are tracked in the subtype line
- Pre-Dominaria planeswalker uniqueness rule (no two planeswalkers with the same planeswalker type) is no longer in effect — ONLY the legend rule applies now
- Loyalty abilities use the stack, but adding/removing loyalty counters as part of the cost doesn't use the stack
- A planeswalker with 0 loyalty entering the battlefield is immediately put into the graveyard as an SBA
- "Can't be countered" on loyalty abilities is not a thing — loyalty abilities CAN be countered if they target and the target is illegal
- The "once per turn" restriction applies per planeswalker, not per player — each planeswalker can have one of its loyalty abilities activated once per turn
- Static abilities on planeswalkers (like "You may cast..." on some planeswalkers) function regardless of loyalty abilities
- Some planeswalkers are also creatures (e.g., "Sarkhan, the Masterless" type effects) — these follow both rulesets
- Planeswalker commander tax works differently — commanders that are planeswalkers with "can be your commander" have commander tax
