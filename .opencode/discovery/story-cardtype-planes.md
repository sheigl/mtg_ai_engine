# Story: Plane Rules (CR 901) — Planechase

## User Story
As a game engine developer, I want Plane rules to function correctly per the Comprehensive Rules, so that Plane cards exist in the command zone, planar die rolling activates them, and chaos/silence abilities function in the Planechase variant.

## Context
Planes are card types used in the Planechase variant. Plane cards start the game in the command zone and are not cast. They are activated by rolling the planar die (from the Planechase set). Each plane has a static ability and a chaos ability (triggered by rolling "chaos" on the planar die). Planes are not permanents — they are command-zone cards with ongoing effects.

### Comprehensive Rules Grounding
- **CR 901.1**: "A plane is a card type used in the Planechase variant."
- **CR 901.2**: "A plane card is not a permanent. It stays in the command zone throughout the game."
- **CR 901.3**: "The planar die has two faces: 'planeswalk' (3 faces) and 'chaos' (3 faces)."
- **CR 901.4**: "When you roll 'planeswalk,' you exile the current plane and reveal the next plane from the planar deck."
- **CR 901.5**: "Each plane has a static ability that is active while the plane is face up in the command zone."
- **CR 901.6**: "Each plane has a chaos ability that triggers when a player rolls 'chaos.'"
- **CR 901.7**: "Players can play the planar die once per turn as a special action."
- **CR 901.8**: "If a card refers to 'the current plane,' it means the face-up plane in the command zone."
- **Example card**: "The Eon Fog" — Plane — "Players skip their untap steps. Whenever you roll {CHAOS}, untap all permanents you control."

## Acceptance Criteria
- [ ] Plane cards exist in the command zone (not on the battlefield) (CR 901.2)
- [ ] Only one plane is face up in the command zone at a time (the "current plane")
- [ ] The planar die can be rolled once per turn as a special action (CR 901.7)
- [ ] Rolling "planeswalk": exile current plane, reveal next from planar deck (CR 901.4)
- [ ] Rolling "chaos": triggers the chaos ability of the current plane (CR 901.6)
- [ ] The current plane's static ability is active while it's face up (CR 901.5)
- [ ] Plane static abilities are continuous effects that apply to the game
- [ ] Chaos abilities go on the stack as triggered abilities
- [ ] Planeswalker creatures can't attack the plane (plane is not a permanent)
- [ ] Planes can be interacted with via "destroy target plane" effects (exist in Planechase)
- [ ] Full regression suite passes

## Dependencies
- Story: Command Zone (CR 400.2) — command zone mechanics
- Story: Triggered Abilities (CR 603) — chaos triggers

## Status: ❌ Not Implemented

Not implemented: `CoreType.PLANE` enum exists at `card_type.py:13`. Zero engine implementation — no Planechase rules, planar deck, planeswalk triggers, or phenomenon interaction.

## Priority: Low

## Notes
- Planechase is a casual variant — implementation priority depends on variant support goals
- The planar die is a special six-sided die — not a standard d6 — with specific faces
- Rolling the planar die is a "special action" — it doesn't use the stack and can't be responded to
- Each plane card has exactly one static ability and one chaos ability
- Planes can have subtypes (e.g., "Plane — Dominaria" or "Plane — Alara")
- The planar deck is a separate deck from the main library, typically containing 10+ plane cards
- Plane static abilities affect ALL players equally (unless specified otherwise)
- Some planes have triggered abilities that aren't labeled "chaos" — these are normal triggered abilities
- If a plane would leave the command zone, it's put into the planar deck's graveyard (not exiled)
- The current plane is part of the game state and should be tracked on GameState
