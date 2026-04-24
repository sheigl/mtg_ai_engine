# ETB Choice Framework (034)

## Overview
Implement choice handling for cards with "as this enters" replacement effects that give the player options (pay life/snow mana, meet condition, etc.) before settling the permanent.

## Problems Being Solved
1. Shock lands pay life → enter tapped by default (wrong)
2. Check lands enter tapped without check (wrong)  
3. Fetch lands don't ask for pay choice (wrong)
4. Snow duals don't ask for snow mana choice (wrong)

## Implementation Plan

### 1. Detection (ability_parser.py / zones.py)
- Add regex patterns to detect all ETB choice types
- Return choice type + alternatives when detected

### 2. Game State (models/game.py)
```python
class ETBChoice(BaseModel):
    permanent_id: str
    player_name: str
    choice_type: str  # "shockland", "checkland", "fetchland", "snow"
    alternatives: list[ChoiceOption]
```

### 3. Resolution (game.py + turn_manager.py)
- Add to pending choices pipeline
- Block passing until choice resolved
- Apply result: tapped vs untapped

### 4. UI (ActivityPanel / ActionPanel.tsx)
- Show choice UI like scry/surveil
- Display consequences to user

### 5. AI (hybrid_game_loop.py)
- Heuristic for each choice type
- Make decision unless override by human

## Testing Strategy
1. Create test games with each land type
2. Verify choice prompts appear
3. Test AI decisions
4. Test hybrid override