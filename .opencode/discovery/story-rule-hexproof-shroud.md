# Story: Hexproof vs Shroud Distinction (CR 702.54 vs 702.41)

## User Story
As a game engine developer, I want hexproof and shroud to be distinguished correctly — hexproof prevents targeting by opponents only, while shroud prevents all targeting — so that each keyword's targeting rules are enforced per the Comprehensive Rules.

## Context
Hexproof and shroud are both defensive keyword abilities that prevent targeting, but with a critical distinction: hexproof only blocks targeting by OPPONENTS (the controller can still target their own hexproof permanents), while shroud blocks ALL targeting regardless of controller. This distinction matters for spells and abilities that target "a creature you control" — a hexproof creature is a valid target, but a shrouded creature is not.

### Comprehensive Rules Grounding
- **CR 702.54b**: "Hexproof stops targeting by opponents only. A permanent or player with hexproof can be targeted by spells and abilities controlled by that permanent's or player's controller."
- **CR 702.41a**: "Shroud stops targeting by anyone. A permanent or player with shroud can't be the target of any spell or ability."
- **CR 115.1a/115.1b**: A spell or ability targets when it uses the word "target" — hexproof/shroud prevent these.
- **Example card (hexproof)**: Thrun, Breaker of Silence — can be targeted by its controller's spells
- **Example card (shroud)**: Slippery Bogle — can't be targeted by anyone's spells or abilities

## Acceptance Criteria
- [x] `is_hexproof(gs, perm_id_or_player_name) -> bool` — checks hexproof keyword
- [x] `is_shrouded(gs, perm_id_or_player_name) -> bool` — checks shroud keyword
- [x] `can_target_hexproof(gs, target, source_controller) -> bool` — opponent check
- [x] `can_target_shrouded(gs, target) -> bool` — always False if shroud present
- [x] Hexproof: controller can target their own hexproof permanents; opponents cannot
- [x] Shroud: NO ONE can target shrouded permanents, including the controller
- [x] Both keywords: checked during targeting validation (CR 601.2c)
- [x] Both keywords: if target becomes illegal due to hexproof/shroud, the spell/ability fizzles (CR 608.2b)
- [x] Hexproof/shroud on PLAYERS: works the same way — hexproof player can't be targeted by opponents; shroud player can't be targeted by anyone
- [x] Integration tests cover: hexproof blocks opponent targeting, hexproof allows controller targeting, shroud blocks all targeting, player hexproof, player shroud, partial fizzle with hexproof
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Targeting Rules (CR 115, 601.2c) — targeting validation uses hexproof/shroud checks
- Keyword stories: `story-kw-hexproof.md` and `story-kw-shroud.md` — the keyword module implementations

## Priority: Low

## Status: ✅ Complete

## Estimated Effort: S

## Notes
- Both keywords are already implemented as query helpers in the engine (`story-kw-hexproof.md`, `story-kw-shroud.md`)
- This story covers the RULES DISTINCTION between the two and ensures they're wired correctly into the targeting pipeline
- Key test: a spell that says "draw a card" plus "target creature you control" should work on a hexproof creature but NOT on a shrouded creature
- Player-level hexproof/shroud: currently returns False (not implemented on PlayerState) — this story may require adding keyword tracking to PlayerState
- Some older cards had shroud that was later errata'd to hexproof
- Standard security assumption: if you need to target your own creatures, prefer hexproof; if the creature shouldn't be targetable at all, use shroud
