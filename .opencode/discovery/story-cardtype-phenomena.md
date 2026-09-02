# Story: Phenomena Rules (CR 702) — Planechase

## User Story
As a game engine developer, I want Phenomena rules to function correctly per the Comprehensive Rules, so that Phenomena cards trigger additional effects when players planeswalk in the Planechase variant.

## Context
Phenomena are a card type used in Planechase (first appearing in Planechase 2012). They are interspersed in the planar deck. When a phenomenon is revealed (via a planeswalk roll of the planar die), it triggers a one-time effect and is then put on the bottom of the planar deck. Phenomena are not permanents and don't stay on the battlefield or command zone.

### Comprehensive Rules Grounding
- **CR 702.1**: "Phenomena are a card type used in Planechase."
- **CR 702.2**: "A phenomenon is not a permanent. It is put into the command zone when revealed, then immediately put on the bottom of the planar deck after its effect resolves."
- **CR 702.3**: "Phenomena have an ability that triggers when the phenomenon is revealed."
- **CR 702.4**: "After a phenomenon's triggered ability resolves, the phenomenon is put on the bottom of the planar deck."
- **CR 702.5**: "Phenomena are shuffled into the planar deck as part of the planar deck."
- **Example card**: "Warp World" — Phenomenon — "When you encounter Warp World, each player shuffles all permanents they own into their library, then reveals that many cards from the top of their library and puts all permanent cards revealed this way onto the battlefield."

## Acceptance Criteria
- [ ] Phenomena cards exist as a distinct card type from Planes
- [ ] When a phenomenon is revealed from the planar deck (via planeswalk roll), it triggers its effect
- [ ] The phenomenon is put into the command zone temporarily, then put on bottom of planar deck after resolution
- [ ] The phenomenon's effect is a triggered ability that goes on the stack and can be responded to
- [ ] Phenomena don't have static abilities — only triggered abilities when revealed
- [ ] Phenomena don't stay in the command zone — they go to the bottom of the planar deck
- [ ] Phenomena are shuffled into the planar deck, not in a separate deck
- [ ] "Encounter" keyword: matching the revealed phenomenon's type
- [ ] Full regression suite passes

## Dependencies
- Story: Plane Rules (CR 901) — Planechase variant foundation
- Story: Triggered Abilities (CR 603) — phenomenon triggers

## Status: ❌ Not Implemented

Not implemented: `CoreType.PHENOMENON` enum exists at `card_type.py:14`. Zero engine implementation.

## Priority: Low

## Notes
- Phenomena are much simpler than Planes — they have a single triggered ability and then leave
- `mtg_engine/models/card_type.py` has `CoreType.PHENOMENON` already defined
- Phenomena are shuffled into the planar deck itself, not in a separate stack
- When the planar die is rolled and a player would planeswalk, the top card of the planar deck is revealed:
  - If it's a Plane: the current plane is exiled, the new plane becomes active
  - If it's a Phenomenon: the phenomenon triggers, resolves, then is put on bottom
- The "encounter" term in Planechase refers to revealing a phenomenon
- Examples of phenomena include: "Warp World," "Morphic Tide," "Mutual Epiphany"
- Implementation priority is very low unless full Planechase support is planned
- Phenomena have a subtype "Phenomenon" — the type line is "Phenomenon" with no further subtypes usually
