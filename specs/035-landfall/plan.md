# Landfall Ability Implementation (035-landfall)

## Problem

Landfall triggered abilities are not firing when a land enters the battlefield under the player's control.

**Example card**: Sazh's Chocobo
- Oracle: "Landfall — Whenever a land you control enters, put a +1/+1 counter on this creature."

## Root Cause Analysis

1. **ability_parser.py**: Does not detect "Landfall" keyword
2. **triggers.py**: `_matches_zone_change()` doesn't match "landfall" conditions
3. **stack.py**: No pattern to resolve "+1/+1 counter on this creature" effect

## Implementation Plan

### 1. Detect landfall keyword (ability_parser.py)
- Add "Landfall" to KEYWORDS detection
- Parse landfall ability with proper trigger condition format

### 2. Match landfall triggers (triggers.py)
- Add LAND_TRIGGER_PATTERNS for "landfall" triggers
- Update `_matches_zone_change()` to detect landfall trigger conditions

### 3. Resolve landfall effects (stack.py)
- Add effect pattern: "put a +1/+1 counter on this creature"
- Use existing counter infrastructure

### 4. Testing
- Test with Sazh's Chocobo
- Verify all player types (human, AI, bot)

## Files Modified
- `mtg_engine/card_data/ability_parser.py`
- `mtg_engine/engine/triggers.py`
- `mtg_engine/engine/stack.py`