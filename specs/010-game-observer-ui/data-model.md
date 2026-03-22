# Data Model: Game Observer Web UI

**Feature**: 010-game-observer-ui
**Date**: 2026-03-21

## Overview

The observer UI is **read-only** — it consumes existing engine data models via the REST API. No new persistent storage or database entities are introduced. This document describes the TypeScript types that mirror the engine's Pydantic models, plus the lightweight summary model for the new game list endpoint.

## Entities

### GameSummary (NEW — backend + frontend)

Lightweight projection of GameState for the game list view. Not stored separately; computed on the fly from in-memory GameState.

| Field | Type | Description |
|-------|------|-------------|
| game_id | string | UUID of the game |
| player1_name | string | Name of player 1 |
| player2_name | string | Name of player 2 |
| format | string | "standard" or "commander" |
| turn | int | Current turn number |
| phase | string | Current phase (e.g. "combat") |
| step | string | Current step (e.g. "declare_attackers") |
| is_game_over | bool | Whether the game has ended |
| winner | string \| null | Winner's name, or null if ongoing |

### GameState (EXISTING — read from API)

Full game state returned by `GET /game/{game_id}`. The frontend mirrors this as a TypeScript interface.

| Field | Type | Description |
|-------|------|-------------|
| game_id | string | UUID |
| turn | int | Current turn number |
| active_player | string | Player whose turn it is |
| priority_holder | string | Player with current priority |
| phase | Phase | Current phase enum |
| step | Step | Current step enum |
| stack | StackObject[] | Spells/abilities awaiting resolution |
| battlefield | Permanent[] | All permanents on the field |
| players | PlayerState[2] | Both players' state |
| pending_triggers | PendingTrigger[] | Unresolved triggers |
| state_hash | string | SHA256 (16 chars) for dedup |
| is_game_over | bool | Game ended flag |
| winner | string \| null | Winner name or "draw" |
| combat | CombatState \| null | Active combat info |
| format | string | "standard" or "commander" |
| commander_damage | dict | Commander damage tracking (commander only) |

### PlayerState (EXISTING — nested in GameState)

| Field | Type | Description |
|-------|------|-------------|
| name | string | Player name |
| life | int | Life total (20 standard, 40 commander) |
| hand | Card[] | Cards in hand (hidden from observer; count visible) |
| library | Card[] | Library (count visible) |
| graveyard | Card[] | Graveyard (visible) |
| exile | Card[] | Exile zone (visible) |
| poison_counters | int | Poison counter total |
| mana_pool | ManaPool | Current mana available |
| lands_played_this_turn | int | Lands played count |
| has_lost | bool | Player eliminated |
| command_zone | Card[] | Commander zone (commander only) |
| commander_name | string \| null | Commander card name |
| commander_cast_count | int | Times commander cast (for tax) |

### Permanent (EXISTING — on battlefield)

| Field | Type | Description |
|-------|------|-------------|
| id | string | UUID (used as animation layoutId) |
| card | Card | Underlying card data |
| controller | string | Controlling player name |
| tapped | bool | Tapped state (rotated 90 degrees in UI) |
| damage_marked | int | Damage on creature |
| counters | dict[string, int] | Counter types and amounts |
| attached_to | string \| null | ID of permanent this is attached to |
| attachments | string[] | IDs of things attached to this |
| is_token | bool | Token flag |
| summoning_sick | bool | Summoning sickness |

### Card (EXISTING — in all zones)

| Field | Type | Description |
|-------|------|-------------|
| id | string | UUID (stable across zone changes — used for layoutId) |
| name | string | Card name (displayed on card element) |
| mana_cost | string \| null | Mana cost string e.g. "{1}{R}{R}" |
| type_line | string | Full type line |
| oracle_text | string \| null | Rules text |
| power | string \| null | Creature power |
| toughness | string \| null | Creature toughness |
| loyalty | string \| null | Planeswalker loyalty |
| colors | string[] | Card colors (W/U/B/R/G) |
| keywords | string[] | Keyword abilities |
| cmc | float | Converted mana cost |

### StackObject (EXISTING — on the stack)

| Field | Type | Description |
|-------|------|-------------|
| id | string | UUID |
| source_card | Card | The spell/ability source |
| controller | string | Who controls this stack object |
| targets | string[] | Target IDs |
| effects | string[] | Effect descriptions |

### TranscriptEntry (EXISTING — for action log)

| Field | Type | Description |
|-------|------|-------------|
| seq | int | Sequence number (monotonic, used for incremental fetching) |
| event_type | string | cast, resolve, trigger, sba, zone_change, damage, phase_change, etc. |
| description | string | Human-readable text (displayed in action log) |
| data | dict | Structured event data |
| turn | int | Turn when event occurred |
| phase | string | Phase context |
| step | string | Step context |

## Relationships

```
GameSummary ←(projection of)── GameState
GameState ──(has 2)── PlayerState
GameState ──(has many)── Permanent (battlefield)
GameState ──(has many)── StackObject (stack)
PlayerState ──(has many)── Card (hand, library, graveyard, exile, command_zone)
Permanent ──(wraps 1)── Card
StackObject ──(references 1)── Card (source_card)
TranscriptRecorder ──(produces many)── TranscriptEntry (per game)
```

## State Transitions

### Card Zone Transitions (trigger animations)

Cards move between zones during gameplay. Each transition should trigger an animation in the UI:

| From | To | Trigger | Animation |
|------|-----|---------|-----------|
| Hand | Battlefield | Play land / Cast creature | Slide from hand area to battlefield |
| Hand | Stack | Cast spell | Slide from hand to stack zone |
| Stack | Battlefield | Creature/artifact/enchantment resolves | Slide from stack to battlefield |
| Stack | Graveyard | Instant/sorcery resolves | Slide from stack to graveyard |
| Battlefield | Graveyard | Creature dies, sacrifice, destroy | Slide to graveyard with fade |
| Battlefield | Hand | Bounce effect | Slide back to hand |
| Battlefield | Exile | Exile effect | Slide to exile zone |
| Library | Hand | Draw card | Slide from library to hand |
| Command Zone | Stack | Cast commander | Slide from command zone to stack |
| Graveyard | Command Zone | Commander dies | Slide to command zone |

### Game Lifecycle (UI state machine)

```
[No Games] → (games appear) → [Game List]
[Game List] → (select game) → [Board View]
[Board View] → (game ends) → [Game Over Display]
[Board View] → (connection lost) → [Reconnecting]
[Reconnecting] → (reconnected) → [Board View]
[Board View] → (back button) → [Game List]
```

## Validation Rules

- All data is validated server-side by the engine's Pydantic models. The frontend trusts the API response schema.
- The frontend should handle missing optional fields gracefully (e.g. `commander_damage` absent in standard format games).
- `state_hash` comparison prevents unnecessary re-renders when the game state hasn't changed between polls.
