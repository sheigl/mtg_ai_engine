# Story: Scry Trigger (CR 701.19)

## User Story
As an MTG engine developer, I want a "scry" trigger pattern with check function and engine wiring, so that cards with "whenever you scry" triggered abilities fire correctly.

## Context
No scry trigger pattern exists in triggers.py. Scry (CR 701.19) is one of the most common action words in MTG — it involves looking at some number of cards from the top of your library and putting any number of them on the bottom. Several cards have "whenever you scry" as a condition.

### Comprehensive Rules Grounding
- **CR 701.19**: "To scry N, a player looks at the top N cards of their library, then puts any number of them on the bottom of their library in any order and the rest on top in any order."
- **Game event**: A player performs the scry action (from an effect or keyword)
- **Example card**: *God-Eternal Kefnet* — "Whenever you scry, you may draw a card."

## Acceptance Criteria
- [ ] Create `SCRY_TRIGGER_PATTERNS` list with regexes matching: "whenever you scry", "whenever a player scries", "whenever (?:this|~) scries"
- [ ] Create `check_scry_triggers(game_state, player_name: str, scry_amount: int)` that queues PendingTriggers
- [ ] Wire into the scry resolution handler in stack.py (where scry N effect resolves)
- [ ] Integration tests: scrying fires trigger, non-scry library look (tutor) does NOT fire
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: Medium

## Estimated Effort: S

## Notes
- Scry is an action, not a keyword — it appears as "Scry N" in oracle text
- The trigger fires when the scry action is taken, not based on the outcome
- Forge's trigger: `ScryTrigger`
