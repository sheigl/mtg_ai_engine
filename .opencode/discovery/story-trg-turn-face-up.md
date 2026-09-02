# Story: Turn Face Up Trigger (CR 702.37)

## User Story
As an MTG engine developer, I want a turn-face-up trigger pattern so that morph/manifest cards with "when ~ is turned face up" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 702.37**: "If a creature has morph or megamorph, its controller may turn it face up by paying its morph cost. When a permanent is turned face up, any abilities that trigger when it's turned face up trigger."
- **Example card**: "When ~ is turned face up, destroy target creature." (e.g., Bane of the Living)

## Acceptance Criteria
- [ ] Add `TURN_FACE_UP_TRIGGER_PATTERNS` regex patterns for "when ~ is turned face up" and "whenever a permanent is turned face up"
- [ ] Add `check_turn_face_up_triggers()` check function
- [ ] Wire into the engine morph/manifest turn-face-up resolution path
- [ ] Integration tests with a morph card that triggers on turning face up
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md
- story-kw-morph.md

## Priority: Low

## Estimated Effort: M
