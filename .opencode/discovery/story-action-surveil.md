# Story: Surveil (CR 701.41)

## User Story
As a game engine developer, I want the surveil action to function correctly per the Comprehensive Rules, so that players can look at the top N cards of their library, put any number into the graveyard, and the rest back on top in any order.

## Context
Surveil is similar to scry but with a critical difference: cards put into the graveyard go to the graveyard, not just to the bottom of the library. This enables graveyard strategies and "whenever you surveil" triggers (such as "Surveil 1 — surveil triggers").

### Comprehensive Rules Grounding
- **CR 701.41a**: "To surveil N, look at the top N cards of your library. Put any number of them into your graveyard and the rest on top of your library in any order."
- **CR 701.41b**: "If a player is instructed to surveil, then an ability triggers 'whenever you surveil,' that ability triggers after the player finishes surveilling."
- **CR 701.41c**: "Surveil N is different from scry N — surveilled cards go to the graveyard, not to the bottom of the library."
- **Example card**: Sinister Sabotage — "Counter target spell. Surveil 1."
- **Example card**: Discovery // Dispersal — "Surveil 2, then draw two cards."
- **See also**: Scry (story-kw-scry.md), Mill (story-action-mill.md)

## Acceptance Criteria
- [x] `surveil(gs, player_name, n)` looks at the top N cards
- [x] Player can choose any number of the surveilled cards to put into graveyard
- [x] Remaining cards are placed on top of library in any order (player's choice)
- [x] For AI players: auto-resolve with heuristic (keep spells/lands, mill excess lands)
- [x] For human players: queue `pending_surveil_choice` with the N cards
- [x] "Whenever you surveil" triggers fire after surveil completes
- [x] Surveil 0 does nothing but still triggers surveil triggers (if any)
- [x] Surveil with fewer cards than N in library surveils as many as possible
- [x] Integration test: surveil 2, mill one card to graveyard, order the other on top
- [x] Integration test: surveil trigger fires when surveilling
- [x] Integration test: empty library surveil (no cards to look at)
- [x] Full regression suite passes

## Dependencies
- Library/graveyard zone management
- Scry (story-kw-scry.md) — related but distinct mechanic
- Trigger system (surveil triggers)

## Priority: High
## Status: ✅ Complete

## Estimated Effort: M
