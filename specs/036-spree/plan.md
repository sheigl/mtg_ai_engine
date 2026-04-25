# Spree Mechanic Implementation (036-spree)

## Problem

Spree is a keyword mechanic from March of the Machine that allows a spell to have multiple optional additional costs. The player chooses one or more modes when casting the spell.

**Example card**: Insatiable Avarice
```
Spree — (Choose one or more additional costs.)
+ {2} — Search your library for a card, then shuffle and put that card on top.
+ {B}{B} — Target player draws three cards and loses 3 life.
```

## Root Cause

1. **ability_parser.py**: Does not detect "Spree" keyword or parse mode options
2. **API (game.py)**: No handling for Spree mode selection choices
3. **stack.py**: No resolution of Spree mode effects

## Implementation Plan

### 1. Detect Spree keyword (ability_parser.py)
- Add "spree" to KEYWORDS detection
- Parse Spree as a keyword with inline modes

### 2. Parse Spree mode options
- Regex pattern: `+ {\cost} — {effect}`
- Extract each mode: cost and effect text
- Store as list of (cost, effect) tuples

### 3. Add Spree choice to API (game.py)
- When casting a Spree card, queue pending choice for mode selection
- Allow selecting one or more modes
- Legal action shows mode options

### 4. Resolve Spree effects (stack.py)
- When Spree mode is selected, apply its effect
- Each mode has its own effect (tutor, draw, damage, etc.)
- Use existing effect patterns for resolution

### 5. AI/Bot support
- game_loop.py: Handle Spree choice actions
- heuristic_player.py: Score and select best mode

## Files Modified
- `mtg_engine/card_data/ability_parser.py` - Keyword detection
- `mtg_engine/api/routers/game.py` - Choice handling
- `mtg_engine/engine/stack.py` - Effect resolution
- `ai_client/game_loop.py` - AI action conversion
- `ai_client/heuristic_player.py` - AI mode selection

## Testing
- Test Insatiable Avarice casting
- Verify mode selection prompt for human
- Verify AI selects appropriate mode
- Verify chosen effect resolves correctly