# Story: Land Rules (CR 305)

## User Story
As a game engine developer, I want land rules to function correctly per the Comprehensive Rules, so that lands can be played once per turn, produce mana, and basic land types grant intrinsic mana abilities.

## Context
Lands are the fundamental mana-producing permanents. A player may play one land per turn during a main phase (unless an effect grants additional land plays). Basic land types (Plains, Island, Swamp, Mountain, Forest) have intrinsic mana abilities defined by the rules. Non-basic lands may have any abilities.

### Comprehensive Rules Grounding
- **CR 305.1**: "A land is a permanent that produces mana."
- **CR 305.2**: "A player may play a land during their main phase when the stack is empty. The land enters the battlefield. A player may play only one land per turn."
- **CR 305.3**: "A player can't play a land on a turn other than their own."
- **CR 305.4**: "Effects may allow a player to play additional lands beyond the first."
- **CR 305.5**: "If a land enters the battlefield tapped, it enters the battlefield tapped. Otherwise, it enters untapped."
- **CR 305.6**: "The basic land types each have an intrinsic mana ability: Plains {T}: Add {W}, Island {T}: Add {U}, Swamp {T}: Add {B}, Mountain {T}: Add {R}, Forest {T}: Add {G}."
- **CR 305.7**: "If an effect says a land is 'every land type,' it gains all intrinsic mana abilities."
- **CR 305.8**: "If a non-basic land gains a basic land type, it gains the intrinsic mana ability of that type."
- **CR 305.9**: "Lands that enter the battlefield tapped may cause triggers that check for tapped permanents."
- **Example card**: Forest — Basic Land — Forest, "{T}: Add {G}"

## Acceptance Criteria
- [x] One land play per turn tracked per player (additional land plays supported via effects)
- [x] Lands can only be played during a main phase when the stack is empty and it's the player's own turn
- [x] Land entering the battlefield follows normal ETB rules (tapped/untapped, triggers, etc.)
- [x] Basic land types (Plains/Island/Swamp/Mountain/Forest) grant intrinsic {T}: Add {W/U/B/R/G} mana abilities
- [x] Non-basic lands with basic land types also gain the corresponding intrinsic mana ability (CR 305.8)
- [x] "Every land type" effect grants all five intrinsic mana abilities (CR 305.7)
- [x] Mana abilities from lands function as mana abilities (don't use the stack)
- [x] Land played count properly interacts with "additional land" effects
- [x] Full regression suite passes

## Dependencies
- Story: Mana Abilities (CR 605) — land mana abilities are mana abilities
- Story: Mana Pool (CR 106, 118) — mana is added to the mana pool

## Status: ✅ Complete

Implemented: One land per turn via `PlayerState.lands_played_this_turn` reset at turn start (`turn_manager.py:143`), enforced in `play_land()` endpoint (`game.py:557-571`). Basic land mana abilities via `resolve_land_mana_ability()` at `mana.py:457-523`. Full mana pool system (`ManaPool` at `models/game.py:84-93`). Basic land creation via `card_factory.py:120-133`.

## Priority: High

## Notes
- The `type_line` parsing in `mtg_engine/models/card_type.py` currently has a note that "Land" is a core type without a specific enum entry — this may need to be addressed
- Basic land types are subtypes, not supertypes — "Basic Land — Forest" has supertype "Basic", core type "Land", subtype "Forest"
- Land mana abilities are the canonical example of mana abilities (CR 605.1a)
- Snow-covered basics should produce snow mana of their color — this interacts with snow mana rules
- The engine's `ManaPool` already has a `snow` field for snow mana tracking
