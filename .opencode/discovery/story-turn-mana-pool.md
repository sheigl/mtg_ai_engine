# Story: Mana Pool / Mana Burn (CR 106, 118)

## User Story
As a game engine developer, I want the mana pool system to function correctly per CR 106 and 118, so that mana empties from players' mana pools as each step and phase ends, and there is no mana burn in current rules.

## Context
Mana is produced by mana abilities (lands, mana dorks, rituals) and added to a player's mana pool. Mana remains in the pool until it is spent or until the current step or phase ends, at which point all unspent mana empties. Unlike the old rules, there is no mana burn (loss of life from unspent mana) in the current Comprehensive Rules. The current engine empties mana pools in `begin_step()` at `turn_manager.py` line 415-419, clearing pools for all steps except untap and cleanup.

### Comprehensive Rules Grounding
- **CR 106.1**: "Mana is produced by mana abilities. Mana is added to a player's mana pool."
- **CR 118.4**: "Mana empties from a player's mana pool as each step and phase ends."
- **CR 118.3**: "There is no such thing as 'mana burn.'"
- **Purpose**: Track available mana for spell/ability payment; clear floating mana between steps/phases

## Acceptance Criteria
- [ ] Mana is correctly added to a player's mana pool from mana abilities (lands, dorks, rituals)
- [ ] Mana pool is represented with color-specific attributes (`W`, `U`, `B`, `R`, `G`, `C`)
- [ ] Unspent mana empties from the pool at the end of each step and phase
- [ ] Mana pool is NOT cleared during untap step (no priority = no mana spending anyway)
- [ ] Mana pool IS cleared during cleanup step
- [ ] No mana burn penalty occurs for unspent mana
- [ ] Mana produced by a spell/ability can be used to pay costs within the same step
- [ ] Mana payment correctly deducts from the appropriate color slots
- [ ] Full regression passes

## Dependencies
- story-turn-priority-system.md (Priority System)

## Status: 🔄 Partial

Implemented: `ManaPool` model at `models/game.py:84-93`. `add_mana()` at `mana.py:256`, `pay_cost()` at `mana.py:232`. Mana pools cleared at step boundaries via `begin_step()` (`turn_manager.py:417-419`). `ManaPoolPersistence` and `mana_doesnt_empty` for effects like Omnath (`models/game.py:17-20,138`).

**Minor bug**: Mana pool clearing excludes CLEANUP step (line 417), but per CR 106.5a mana should also empty during CLEANUP. This means mana incorrectly persists through CLEANUP into the next turn's untap step.

## Priority: High
