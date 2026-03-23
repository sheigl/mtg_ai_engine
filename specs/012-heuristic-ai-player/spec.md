# Feature Specification: Heuristic AI Player

**Feature Branch**: `012-heuristic-ai-player`
**Created**: 2026-03-22
**Status**: Draft
**Input**: User description: "I would like to create the option of playing an AI opponent that is based on heuristics rather than an LLM. I would like to be able to choose it to play an LLM opponent, or 2 heuristics AI can play each other etc etc"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start a Game With a Heuristic Opponent (Priority: P1)

A user wants to run a game where one or both players are driven by a fast, competitive, rule-based heuristic engine rather than an LLM. They launch the AI client and specify via CLI flags which player(s) use heuristics vs an LLM, then watch the game play out automatically.

**Why this priority**: This is the core deliverable — without the ability to select a heuristic player, nothing else in this feature is usable.

**Independent Test**: Can be fully tested by starting a game with `--player1-type heuristic` and verifying that the game completes without calling any external LLM endpoint.

**Acceptance Scenarios**:

1. **Given** a game with player1 set to heuristic and player2 set to LLM, **When** the game starts, **Then** player1 makes decisions immediately without any API calls, while player2 calls the configured LLM endpoint.
2. **Given** a game with both players set to heuristic, **When** the game starts, **Then** the game completes end-to-end with no LLM calls and no manual input required.
3. **Given** a game with both players set to LLM (existing behaviour), **When** the game starts, **Then** behaviour is identical to the current implementation.

---

### User Story 2 - Heuristic Player Makes Competitive, Optimal Decisions (Priority: P2)

The heuristic player should be a genuinely challenging opponent — capable of defeating an LLM opponent that makes suboptimal plays. It evaluates board state, life totals, card values, combat math, and tempo to always choose the highest-impact action available. It should maximise mana efficiency every turn, apply consistent pressure when ahead, trade resources favourably, and avoid board states that lead to losing positions.

**Why this priority**: A weak heuristic is not useful as a benchmark or opponent. The value of this feature is that the heuristic player provides a reliable, fast, strong baseline opponent.

**Independent Test**: Can be tested by running a heuristic-vs-heuristic game and observing that both players consistently develop their board, apply pressure, make favourable trades in combat, and the game resolves to a winner through strategic play rather than random passing.

**Acceptance Scenarios**:

1. **Given** a heuristic player's main phase with mana available, **When** multiple spells are castable, **Then** the player selects the spell that maximises board impact — preferring the highest-power threat when ahead, and prioritising removal or disruption when behind.
2. **Given** a heuristic player in the declare-attackers step, **When** attacking deals lethal damage, **Then** the player declares exactly the attackers needed to achieve lethal.
3. **Given** a heuristic player in the declare-attackers step with no lethal available, **When** the player has creatures with power greater than the opponent's blockers' toughness (favourable trade), **Then** the player attacks to force favourable trades or accumulate chip damage.
4. **Given** a heuristic player in the declare-blockers step with multiple incoming attackers, **When** blocking, **Then** the player assigns blockers to maximise survival: blocking lethal attackers first, then making favourable trades (kill a larger threat with a smaller blocker) where it improves the board state.
5. **Given** a heuristic player evaluating whether to attack, **When** attacking would result in losing key creatures to unfavourable blocks with no compensating damage, **Then** the player holds back those creatures rather than attacking into a losing trade.
6. **Given** a heuristic player with no beneficial action available, **When** any priority window arises, **Then** the player passes priority promptly.

---

### User Story 3 - Mixed Game Configurations via CLI (Priority: P3)

Users can configure any combination of player types (heuristic or LLM) for either player seat from the command line, without editing configuration files.

**Why this priority**: Flexibility in configuration enables all the use cases (heuristic vs heuristic, heuristic vs LLM, LLM vs LLM), but the underlying engine is more valuable than the CLI ergonomics.

**Independent Test**: Can be tested by running three separate invocations (LLM vs LLM, LLM vs heuristic, heuristic vs heuristic) and confirming each completes without error.

**Acceptance Scenarios**:

1. **Given** the CLI, **When** a user passes `--player1-type heuristic --player2-type llm`, **Then** player 1 uses heuristics and player 2 uses the specified LLM endpoint.
2. **Given** the CLI, **When** no player type is specified, **Then** both players default to LLM (backwards-compatible behaviour).
3. **Given** the CLI, **When** `--help` is shown, **Then** the player type options and their accepted values are documented.

---

### Edge Cases

- What happens if the heuristic player encounters a game state it has no scoring rule for (e.g., an unusual triggered ability)? It falls back to passing priority rather than crashing.
- How does the heuristic player behave when multiple actions score equally? It picks deterministically (e.g., first in list) to avoid non-determinism.
- What if a heuristic player's flags are given but the other player's LLM endpoint is unreachable? The LLM player falls back to passing (existing behaviour) — the heuristic player is unaffected.
- How are heuristic decisions represented in the debug panel? They appear in the Action Log as plain action entries; no prompt/response block is shown since there is no LLM interaction.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support a heuristic player type that makes all game decisions locally using rule-based logic, with no external API calls.
- **FR-002**: Users MUST be able to configure each player seat independently as either `heuristic` or `llm` via CLI flags.
- **FR-003**: The heuristic player MUST play a land from hand during the main phase if it has not yet played a land this turn and has an unplayed land available.
- **FR-004**: The heuristic player MUST evaluate all castable spells and select the one with the highest board impact, using a scoring function that accounts for power/toughness, keywords, and mana efficiency.
- **FR-005**: The heuristic player MUST calculate combat outcomes before declaring attackers: attack when it achieves lethal, when it forces favourable trades, or when it applies uncontested chip damage; hold back when attacking leads to unfavourable losses.
- **FR-006**: The heuristic player MUST assign blockers strategically: prioritise blocking lethal threats first, then make favourable trades (kill a larger attacker at the cost of a smaller blocker), and avoid blocking into losing trades where the heuristic can take the damage.
- **FR-007**: The heuristic player MUST pass priority in any situation where no scored action improves the game state.
- **FR-008**: When no player type flags are specified, the system MUST default to LLM for both players, preserving full backwards compatibility.
- **FR-009**: The system MUST support all three combinations: heuristic vs heuristic, heuristic vs LLM, and LLM vs LLM.
- **FR-010**: The heuristic player MUST respond within a negligible time (no network or model inference latency).
- **FR-011**: The heuristic player MUST maximise mana efficiency each turn — spending as close to all available mana as possible, preferring combinations of spells over a single undercosted spell where the engine permits multiple actions per priority window.

### Key Entities

- **PlayerType**: Enumeration of player decision-making strategies (`llm`, `heuristic`). Each player seat is assigned one type at game start.
- **HeuristicPlayer**: A player implementation that scores each legal action using a weighted evaluation function over board state, life totals, and card values, selecting the highest-scoring action — no external calls, fully deterministic.
- **ActionScore**: A numeric value assigned to a legal action by the evaluation function. Higher is better. Ties broken by action index.
- **PlayerConfig**: Extended to include `player_type` alongside the existing `name`, `model`, and `base_url` fields. For heuristic players, `model` and `base_url` are not required.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A heuristic-vs-heuristic game completes to a winner within 50 turns on any standard mono-colour deck without manual intervention.
- **SC-002**: Heuristic player decisions are made in under 50 milliseconds per priority window.
- **SC-003**: All three player-type combinations can be started and completed using only CLI flags, with no code changes required.
- **SC-004**: Existing LLM-only game invocations (no player-type flags) behave identically to the current implementation.
- **SC-005**: The heuristic player wins at least 40% of games against a default LLM opponent on equal decks, demonstrating genuine competitive strength.
- **SC-006**: The heuristic player never makes an obviously losing play when a winning play is available (e.g., never fails to declare lethal attackers when lethal is achievable).

## Assumptions

- The heuristic evaluation function scores actions based on information available in the legal actions list and game state dict — no lookahead or search tree is required for the initial implementation.
- Combat scoring uses power/toughness values from the game state; keywords such as trample, deathtouch, and first strike are accounted for where visible in card data.
- The heuristic player does not need to handle complex targeting decisions for triggered abilities; these fall back to passing priority.
- Deck composition for heuristic testing uses the same mono-colour creature decks already supported by the engine.
- The debug panel and Action Log show heuristic decisions as plain action entries without a prompt/response block, since there is no LLM prompt to display.
- For heuristic players, the `--player-url` and `--player-model` flags are not required and can be omitted.
