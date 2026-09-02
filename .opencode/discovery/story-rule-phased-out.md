# Story: Phased Out Permanents (CR 702.26)

## User Story
As a game engine developer, I want phased-out permanents to be treated as though they don't exist — they can't affect the game, be targeted, or count for anything — and they phase in on their controller's next untap step per CR 702.26.

## Context
Phasing is a keyword ability that phases permanents in and out before the untap step. A phased-out permanent is treated as though it doesn't exist by the game: it can't be targeted, doesn't count for "counts of permanents," doesn't produce abilities or effects, and doesn't trigger. A phased-out permanent remains in its controller's control but in a "phased-out" state — it phases in during its controller's next untap step.

### Comprehensive Rules Grounding
- **CR 702.26a**: "Phasing is a static ability. 'Phasing' is the keyword that represents this ability."
- **CR 702.26d**: "Phased out permanents are not treated as existing by the game. They can't be targeted, don't count for effect purposes, and don't produce abilities or triggered effects."
- **CR 702.26e**: "A permanent that phases in returns to the battlefield under its owner's control and is treated as though it was on the battlefield continuously."
- **CR 702.26i**: "Phasing happens before the untap step of each turn."
- **Example card**: Erratic Portal — "Phasing (This phases in or out before your untap step.)"

## Acceptance Criteria
- [ ] Phasing check/trigger fires before the untap step of each turn (CR 702.26i)
- [ ] A permanent with phasing phases out (ceases to exist for game purposes)
- [ ] A phased-out permanent phases in (returns to battlefield)
- [ ] Phased-out permanents are tracked in a `phased_out: list[Permanent]` field on GameState
- [ ] Phased-out permanents can't be targeted (targeting system ignores them)
- [ ] Phased-out permanents don't count for "counts of permanents" effects
- [ ] Phased-out permanents don't trigger or produce abilities
- [ ] Phased-out permanents have no zone (they're "phased out," not in any game zone)
- [ ] Phased-out tokens DON'T cease to exist (they phase in later)
- [ ] Phasing in: permanent returns as though it was there continuously (summoning sickness not reset for existing creatures)
- [ ] Integration tests cover: phasing out, phasing in, targeting phased-out, phased-out doesn't count, token phasing, controlled timing (before untap)
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: State-Based Actions (CR 704) — tokens in phased-out state DON'T cease to exist (exception to CR 110.7g)
- Story: Token Rules (CR 110.5-110.8) — token phasing behavior

## Priority: Medium

## Status: ❌ Not Implemented

### Gap Description
Permanent model has phased_out and has_phasing fields, but no engine code implements phasing mechanics. There is no phasing step before untap, no phase-in/phase-out logic, no phased-out state handling (can't be targeted, don't count for effects), and no phasing integration into the turn structure. The fields are unused placeholders.

## Estimated Effort: M

## Notes
- Phasing is a retro mechanic (from Mirage block) but has modern reprints (Teferi's Protection makes YOUR permanents phase out!)
- The phased-out state is NOT a zone — it's an "out-of-game" state similar to exile but reversible
- Crucial: phased-out tokens do NOT cease to exist (CR 702.26d exception to CR 110.7g)
- Phasing in doesn't trigger "enters the battlefield" effects — the permanent is treated as continuous
- A phased-out creature's summoning sickness is maintained (if it had it when it phased out, it still has it when it phases in)
- Auras/equipment on a phased-out creature phase out too (they phase out with what they're attached to)
- Multiple phased-out permanents can exist simultaneously; each phases in independently on its controller's untap step
- The engine's `story-kw-phasing.md` covers the keyword implementation — this story covers the comprehensive phased-out state rules
