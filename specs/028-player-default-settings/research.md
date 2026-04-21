# Research: Player Default Settings

**Feature**: 028-player-default-settings
**Date**: 2026-04-20

## Unknowns Resolved

### 1. How should defaults be applied at game creation time?

**Decision**: Defaults are fetched from MongoDB at game creation time and merged into the existing request payload. If MongoDB is not configured or no defaults exist, the request proceeds with its original values (no failure).

**Rationale**:
- The existing game creation flow (`GameManager.create_game`) is synchronous and must not block on async I/O inside the manager.
- The routers (`game.py`, `human_game.py`, `ai_game.py`) are the right place to fetch defaults asynchronously before calling `create_game`.
- This preserves backward compatibility: games work fine without MongoDB or defaults.

**Alternatives considered**:
- Fetch defaults inside `GameManager.create_game` — rejected because `create_game` is sync and would require thread-safe event-loop hacks.
- Fetch defaults lazily inside the AI client — rejected because it would duplicate logic across AI client and backend, and human players also need defaults.

### 2. What player type keys should be used for defaults?

**Decision**: Use the API-facing player type strings: `human`, `ai`, `heuristic`.

**Rationale**:
- The spec explicitly says "configurable per player type (human, ai, heuristics)".
- The `HumanGameRequest` validator already accepts these three values.
- Internally, `heuristic` and `llm` are both persisted as `"ai"`, but the settings system must distinguish them because heuristic and LLM players have completely different configuration needs (e.g., `AiPersonalityProfile` vs. `base_url`/`model`).

**Alternatives considered**:
- Use persistence labels (`human`, `ai`) — rejected because it would conflate heuristic and LLM settings, which are structurally different.

### 3. What should the settings payload structure look like?

**Decision**: A flat-ish JSON object keyed by setting name. The schema is enforced by Pydantic models per player type, but stored as a flexible dict in MongoDB to allow future extension without migration.

**Rationale**:
- Human players need minimal settings (e.g., auto-tap preferences, UI options).
- AI/LLM players need `base_url`, `model`, `enable_thinking`.
- Heuristic players need `AiPersonalityProfile` fields.
- A single rigid schema would force all types to share fields that don't apply to them.

**Alternatives considered**:
- Strict typed MongoDB schema per player type — rejected because it adds migration burden when new settings are added.
- Separate collections per player type — rejected because it complicates the API (three endpoints instead of one parameterized endpoint).

### 4. Should defaults override request values or supplement them?

**Decision**: Request values take precedence over defaults. Defaults fill in only missing fields.

**Rationale**:
- This matches the spec's P2 user story: "Individual players can have their own settings that override the default settings."
- The request body is the most specific source of truth; defaults are a fallback.

**Alternatives considered**:
- Defaults always override requests — rejected because it would make the API unusable for one-off custom configurations.

### 5. How should validation work?

**Decision**: Validate settings payload against Pydantic models per player type on write. Reject invalid keys/values with a 422 response.

**Rationale**:
- Pydantic v2 is already the validation layer in the project.
- Per-type models give clear error messages (e.g., "`chance_to_attack_into_trade` must be <= 1.0").

**Alternatives considered**:
- Free-form dict with no validation — rejected because it would allow garbage data and silent failures.

## Technology Choices

| Technology | Decision | Rationale |
|---|---|---|
| MongoDB collection name | `player_defaults` | Follows existing naming convention (plural snake_case). |
| Index | unique index on `player_type` | Guarantees one defaults document per player type. |
| Pydantic models | `HumanPlayerSettings`, `AiPlayerSettings`, `HeuristicPlayerSettings` | Type-safe validation, one model per player type. |
| API response envelope | `{"data": ...}` | Matches existing project convention (`game_records.py`, `human_game.py`). |
