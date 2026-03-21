# Data Model: Play-by-Play Game Log

**Feature**: 007-play-by-play-log
**Date**: 2026-03-21

## Entities

### TranscriptEntry *(existing — extended)*

A single recorded game event. Already exists in `mtg_engine/export/transcript.py`.

| Field       | Type   | Description                                                                 |
|-------------|--------|-----------------------------------------------------------------------------|
| seq         | int    | Monotonically increasing sequence number within the game                    |
| event_type  | str    | Event category (see Event Types below)                                      |
| description | str    | Human-readable sentence describing the event                                |
| data        | dict   | Structured payload specific to each event type                              |
| turn        | int    | Turn number when the event occurred                                         |
| phase       | str    | Phase name (e.g., `precombat_main`)                                         |
| step        | str    | Step name (e.g., `declare_attackers`)                                       |

**Event Types (extended)**:

| event_type     | Existing? | New Fields in `data`                                              |
|----------------|-----------|-------------------------------------------------------------------|
| cast           | yes       | player, card_name, targets                                        |
| resolve        | yes       | card_name, controller                                             |
| trigger        | yes       | source_card, controller, effect                                   |
| sba            | yes       | sba_type, description                                             |
| zone_change    | yes       | card_name, from_zone, to_zone, player                             |
| damage         | yes       | source, target, amount                                            |
| phase_change   | yes       | turn, phase, step                                                 |
| priority_grant | yes       | player                                                            |
| choice_made    | yes       | player, choice_type, selection                                    |
| **life_change**    | **NEW**   | player, delta (negative = damage), source, new_total             |
| **draw**           | **NEW**   | player *(card identity omitted — private information)*            |
| **game_end**       | **NEW**   | winner, reason (e.g., "life_total_zero", "decked", "concession") |

---

### VerboseLogger *(new)*

A per-game component that subscribes to `TranscriptEntry` events and emits formatted text output when enabled.

| Field / Method       | Type/Signature                             | Description                                                      |
|----------------------|--------------------------------------------|------------------------------------------------------------------|
| _enabled             | bool                                       | Whether output is currently active                               |
| _logger              | logging.Logger                             | Standard Python logger (channel: `mtg_engine.verbose`)           |
| enable()             | → None                                     | Turn on output; next event will produce a line                   |
| disable()            | → None                                     | Turn off output; no further lines until re-enabled               |
| is_enabled           | bool (property)                            | Current enabled state                                            |
| on_event(entry)      | TranscriptEntry → None                     | Called by game loop with each new transcript entry               |
| _format(entry)       | TranscriptEntry → str \| None              | Convert an entry to a display string; returns None for suppressed events (e.g., priority_grant) |

**Suppressed events** (never printed even when enabled): `priority_grant` (FR — priority passes not logged individually per edge-case spec).

---

### GameManager *(modified)*

Stores one `VerboseLogger` per game.

| New Field / Method         | Type/Signature                            | Description                                       |
|----------------------------|-------------------------------------------|---------------------------------------------------|
| _verbose_loggers           | dict[str, VerboseLogger]                  | game_id → VerboseLogger                           |
| create_game(..., verbose)  | verbose: bool = False → GameState         | Creates VerboseLogger for the game; enables if True |
| get_verbose_logger(gid)    | str → VerboseLogger                       | Returns logger for a game; raises KeyError if missing |
| set_verbose(gid, enabled)  | str, bool → None                          | Enables or disables logging for an existing game  |

---

## State Transitions

```
VerboseLogger state:
  disabled ──enable()──→ enabled
  enabled ──disable()──→ disabled
  (either) ──game ends──→ (disabled automatically to prevent dangling output)
```

## Validation Rules

- `life_change.delta` must be non-zero; zero-delta events are not recorded.
- `game_end.reason` must be one of: `life_total_zero`, `decked`, `concession`, `poison_counters`.
- `draw` entries never include card identity (private information rule).
- `VerboseLogger.on_event` is a no-op when `_enabled` is False — no string formatting occurs.
