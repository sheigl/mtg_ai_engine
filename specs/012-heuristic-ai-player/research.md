# Research: Heuristic AI Player

**Branch**: `012-heuristic-ai-player` | **Date**: 2026-03-22

## Decision 1: Interface Strategy — Duck Typing vs Formal Base Class

**Decision**: Duck typing peer (no base class)

**Rationale**: `GameLoop` already uses duck typing. The only contract it requires is `decide(prompt) -> tuple[int, str]` and a mutable `_debug_callback` attribute. Introducing a formal `BasePlayer` ABC would require modifying `AIPlayer`, `GameLoop`, and `__main__.py` more invasively. Python's structural subtyping means a matching interface is sufficient.

**Alternatives considered**:
- `Protocol` class — cleaner type hints but adds a new file and changes the type annotation in GameLoop; no runtime benefit
- `ABC` base class — enforces contract at class definition time but is overkill for two concrete implementations

---

## Decision 2: How Heuristic Player Accesses Game State

**Decision**: Extend `decide()` with optional `legal_actions: list[dict] | None` and `game_state: dict | None` kwargs

**Rationale**: The heuristic player needs structured access to the legal actions list (not the rendered prompt string). The simplest approach is to pass the raw data as optional extra kwargs to `decide()`. `AIPlayer` adds these to its signature but ignores them. `GameLoop` always passes them. This avoids parsing the prompt string and keeps both player types compatible.

**Alternatives considered**:
- Parse prompt string in HeuristicPlayer — fragile, couples heuristic logic to prompt formatting
- Store legal_actions on the player instance before calling decide() — mutable shared state, error-prone
- Separate method `decide_with_context(prompt, legal_actions, game_state)` — would require changes to GameLoop's call site and the type annotation, same invasiveness as the chosen approach

---

## Decision 3: Score-Based Evaluation Over Fixed Priority Order

**Decision**: Assign a numeric score to every legal action using a weighted evaluation function; select the highest-scoring action. No fixed priority chain.

**Rationale**: The heuristic player must be genuinely competitive. A fixed priority order (always play land → always cast → always attack) produces predictable, easily-exploited behaviour and makes poor situational decisions — for example, attacking into a losing trade because "attack" is always above "pass". A scoring function can represent trade-offs: attacking for lethal scores extremely high, but attacking into a board wipe scores low. This produces a player that feels like a skilled opponent rather than a script.

**Key scoring signals**:
- **Lethal detection**: Attacking for lethal overrides all other considerations (score = 10,000)
- **Mana efficiency**: Higher-CMC spells score more — maximises board development per turn
- **Combat simulation**: Each attacker/blocker assignment is evaluated for net board advantage before committing
- **Keyword weighting**: Deathtouch, trample, lifelink, flying add strategic value to spell selection
- **Life pressure**: Aggressive creatures score higher when opponent is at low life

**Alternatives considered**:
- Fixed priority order — fast to implement but produces exploitable, non-competitive play; rejected in favour of scoring
- Full minimax/alpha-beta search — optimal but requires significant complexity and game tree traversal; not needed for a strong heuristic baseline

---

## Decision 4: CLI Flag Design

**Decision**: `--player1-type` and `--player2-type` flags (separate from existing `--player` flag)

**Rationale**: The existing `--player "name,url,model"` format is a single string; adding a fourth positional field would break existing invocations. Separate `--player1-type` / `--player2-type` flags default to `llm`, so all existing CLI usage is unaffected.

**Alternatives considered**:
- Add fourth field to `--player` string (e.g., `"name,url,model,heuristic"`) — breaks backwards compatibility
- Single `--heuristic-players` flag listing player names — less explicit, harder to validate

---

## Decision 5: What to Show in Action Log / Debug Panel for Heuristic Players

**Decision**: Log heuristic decisions as plain action entries in the Action Log; skip the debug panel prompt/response block entirely

**Rationale**: The heuristic player produces no LLM prompt or streamed response. The `_debug_callback` attribute exists but will not be called (or can be called with a brief "Heuristic decision" entry). The Action Log already shows every action taken regardless of player type, so coverage is maintained.

**Alternatives considered**:
- Post a special "heuristic" debug entry type to the debug panel — adds UI complexity for a non-LLM player; not in scope for this feature
