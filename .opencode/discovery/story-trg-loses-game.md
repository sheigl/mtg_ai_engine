# Story: Loses Game Trigger (CR 104.3)

## User Story
As an MTG engine developer, I want a loses-game trigger pattern so that niche cards that care about losing the game can trigger effects before that happens.

## Comprehensive Rules Grounding
- **CR 104.3**: "A player can't lose the game while an effect states that the player can't lose the game."
- **Example card**: "When you lose the game, you may have target opponent also lose the game." (Hypothetical / Lich-style effect)

## Acceptance Criteria
- [ ] Add `LOSES_GAME_TRIGGER_PATTERNS` regex patterns for "when you lose the game" and "whenever you would lose the game"
- [ ] Add `check_loses_game_triggers()` check function
- [ ] Wire into the engine game-loss check path
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M
