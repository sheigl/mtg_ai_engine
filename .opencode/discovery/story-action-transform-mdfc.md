# Story: Transform / MDFC (CR 711)

## User Story
As a game engine developer, I want transform and Modal Double-Faced Cards (MDFCs) to function correctly per the Comprehensive Rules, so that double-faced cards can transform under specified conditions.

## Context
This game action is already fully documented under the game mechanic story `story-gm-mdfc.md`. This file serves as an action-oriented reference.

### Comprehensive Rules Grounding
- **CR 711.1**: "Modal double-faced cards have two faces, one on each side. Each face has its own characteristics."
- **CR 711.2a**: "A player may cast either face of a modal DFC."
- **CR 711.10a**: "To transform a permanent, turn it over so its other face is up."
- **CR 701.27b**: "To transform a permanent, turn it so its other side is face up."
- **Example card**: Jadar, Ghoulcaller of Nephalia // Jadar, Zombie Lord

## Acceptance Criteria
- [ ] See `story-gm-mdfc.md` for full acceptance criteria
- [ ] Transform flips the permanent from one face to the other
- [ ] MDFCs start on the face chosen when cast
- [ ] Daybound/nightbound cards transform via day/night cycle

## Dependencies
- story-gm-mdfc.md (full game mechanic story)
- story-gm-day-night.md (for daybound/nightbound)
- story-rule-transform.md (rules details)

## Priority: High
## Status: ❌ Not Implemented

> **Gap**: Transform triggers exist in triggers.py and day/night transforms work. But no general `transform()` function for arbitrary transform effects. MDFC casting with face choice not fully implemented — cast_spell uses generic face_index without MDFC-specific validation per CR 711.

## Estimated Effort: L
