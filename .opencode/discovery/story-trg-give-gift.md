# Story: Give Gift Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a give gift (promise a gift) trigger pattern so that Wilds of Eldraine cards with "when you promise a gift" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR TBD**: Gift is a mechanic from Wilds of Eldraine where a player may promise an opponent a gift token when casting a spell. If they do, the opponent gets a Gift token when the spell resolves.
- **Example card**: Various Wilds of Eldraine cards — "When you promise a gift, scry 1."

## Acceptance Criteria
- [ ] Add `GIVE_GIFT_TRIGGER_PATTERNS` regex patterns for "when you promise a gift" and "whenever you give a gift"
- [ ] Add `check_give_gift_triggers()` check function
- [ ] Wire into the engine gift resolution path
- [ ] Integration tests with a card that triggers on gifting
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M
