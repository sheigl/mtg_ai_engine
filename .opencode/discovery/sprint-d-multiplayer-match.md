# Sprint D: Multiplayer Rules Foundation and Match System

## Overview
Build foundational support for 3+ player games (Commander's primary format) and a best-of-3 sideboarding match system. These are structural changes that affect game creation, turn management, combat resolution, and the API layer. This sprint establishes the scaffolding — advanced multiplayer rules (e.g., commander damage with multiple opponents, team games) can be layered on in future sprints.

---

## User Stories

### SD-01: Multiplayer Game Creation and Turn Order

**User Story**
As a Commander player, I want to create games with 3 or 4 players so that I can play multiplayer Commander formats.

**Context**
The engine currently supports exactly 2 players. The `GameState.players` field is a list of `PlayerState`, but game creation (`POST /game`) only accepts `player1_name`, `player2_name`, `deck1`, `deck2`. Turn management (`turn_manager.py`) assumes a fixed 2-player rotation: active player alternates between the two players each turn.

For multiplayer, we need:
- Variable player count (2–8 per CR 101.4)
- Deterministic turn order based on game creation order or random assignment
- Proper phase/step cycling for all players

**Acceptance Criteria**
- [ ] `POST /game` API accepts variable number of players:
  - [ ] New request model supports `"players": [{"name": "Alice", "deck": [...]}, {"name": "Bob", "deck": [...]}]` format (backward-compatible with existing 2-player `player1_name`/`player2_name`)
  - [ ] Minimum 2 players, maximum 8 players per CR 101.4
  - [ ] Each player gets a unique `player_number` (0-indexed) for turn order reference
- [ ] `GameState` gains:
  - [ ] `turn_order: list[str]` — ordered list of player names defining who takes turns in what sequence
  - [ ] `current_turn_index: int = 0` — index into `turn_order` for the current active player's turn
- [ ] Turn manager (`turn_manager.py`) updated to cycle through `turn_order`:
  - [ ] Beginning of each new turn, `active_player` is set to `turn_order[current_turn_index]`
  - [ ] End of turn advances `current_turn_index = (current_turn_index + 1) % len(turn_order)`
- [ ] Priority passing works correctly with N players:
  - [ ] When a player passes priority, it goes to the next player in `turn_order` (not just "the other player")
  - [ ] Stack resolves only when ALL players have passed priority in sequence
- [ ] >= 5 tests covering: 3-player game creation, 4-player game creation, turn order cycles correctly through all players, priority passes to correct next player, backward compatibility with 2-player games

**Dependencies**: None (foundational for SD-02 and SD-03)

**Priority: High** — Required for any multiplayer functionality

**Estimated Effort**: 4-6 hours

---

### SD-02: Multiplayer Combat Resolution

**User Story**
As a player in a multiplayer game, I want to declare attackers against a single defending player so that combat works correctly with multiple opponents.

**Context**
In Commander (and most multiplayer formats), each turn has one active player and one defending player chosen by the active player. The current combat system (`combat/core.py`) assumes the defender is always "the other player." For multiplayer:
- Active player chooses which opponent to attack at the beginning of combat
- Only the defending player can declare blockers for that combat
- Combat damage is dealt only between attackers and the chosen defender's blockers

**Acceptance Criteria**
- [ ] `GameState` gains `defending_player: str | None = None` field — set at start of combat, cleared at end of combat
- [ ] Beginning of combat phase (declare blockers step):
  - [ ] For human player: queue `pending_defender_choice` with list of valid defending players (all opponents)
  - [ ] Legal actions include `defend_{player_name}` for each opponent
  - [ ] For AI player: auto-select defender using heuristic (e.g., player with highest life, or player who dealt most damage recently)
- [ ] Combat declaration (`declare_attackers`) updated to use `defending_player` instead of hardcoded "other player"
- [ ] Blocker assignment (`declare_blockers`) only allows the defending player's creatures to block
- [ ] Combat damage is assigned only between attacking creatures and blocking creatures (plus unblocked damage to defending player)
- [ ] Monarch combat damage hook updated: if active player deals combat damage to monarch, monarch transfers regardless of whether monarch is the defending player
- [ ] >= 5 tests covering: defender choice presented for human, AI auto-selects defender, only defender can block, damage goes to correct player, monarch transfer works with non-defending monarch

**Dependencies**: SD-01 (requires multiplayer game state and turn order)

**Priority: High** — Combat is the core interaction in any MTG game

**Estimated Effort**: 4-6 hours

---

### SD-03: Multiplayer Targeting and Spell Resolution

**User Story**
As a player in a multiplayer game, I want spells and abilities to correctly identify valid targets across all players so that targeting works with multiple opponents.

**Context**
The current targeting system assumes 2 players — "any target" typically means the active player's permanents, the opponent's permanents, or either player. For multiplayer:
- "Target player" can be any of N players (including self in some cases)
- "Target creature" can be any creature on battlefield regardless of controller (unless restricted by text)
- Hexproof/Shroud targeting validation must account for source controller vs target controller across all players

**Acceptance Criteria**
- [ ] `_compute_legal_actions()` legal targets are computed against ALL players' permanents and player states, not just "the opponent"
- [ ] Targeting validation in hexproof/shroud (`can_target_hexproof`, `can_target_shrouded`) works correctly with N players:
  - [ ] Hexproof blocks targeting by any opponent (not just one specific opponent)
  - [ ] Shroud blocks targeting by anyone including controller
- [ ] Spell resolution pushes correct target information onto stack objects for N-player games
- [ ] "Target player you don't control" legal actions exclude the active player and include all other players
- [ ] >= 4 tests covering: target any player in 3-player game, hexproof blocks all opponents, shroud blocks self too, targeting validation with multiple creatures controlled by different players

**Dependencies**: SD-01 (requires multiplayer game state)

**Priority: Medium** — Important for correctness but less visible than combat

**Estimated Effort**: 2-4 hours

---

### SD-04: Sideboarding and Best-of-3 Match System

**User Story**
As a competitive player, I want to play best-of-3 matches with sideboarding between games so that I can adjust my strategy based on the opponent's deck.

**Context**
The engine currently has no concept of "matches" — each game is standalone. A best-of-3 match requires:
1. Creating a match container that tracks individual games and their results
2. Between games, allowing players to exchange cards between main deck and sideboard (sideboarding)
3. Enforcing sideboarding rules: main deck must be 60 cards (Standard/Modern/etc.) or 100 cards (Commander), sideboard up to 15 cards (or 0 for Commander without specific rules)
4. Tracking match score (first to 2 wins in BO3)

**Acceptance Criteria**
- [ ] New `Match` model with fields:
  - [ ] `match_id`: str — unique identifier
  - [ ] `format`: str — game format (determines deck/sideboard sizes)
  - [ ] `players`: list of player names
  - [ ] `games_won`: dict[str, int] — per-player win count
  - [ ] `best_of`: int — match length (default 3)
  - [ ] `current_game_number`: int — which game in the series is active
  - [ ] `status`: "in_progress" | "completed"
- [ ] New API endpoints:
  - [ ] `POST /match` — create a new match with player decks and sideboards; automatically creates first game
  - [ ] `GET /match/{match_id}` — get match status, game results, current score
  - [ ] `POST /match/{match_id}/sideboard` — submit sideboard changes between games (specify cards to move from main ↔ side)
  - [ ] `POST /match/{match_id}/next-game` — create next game in series with updated decks
- [ ] Sideboarding validation:
  - [ ] Main deck must remain at legal size after swap (60 for Standard/Modern/etc., 100 for Commander)
  - [ ] Total cards (main + side) cannot exceed original combined count
  - [ ] Singleton rules enforced: max 4 copies of any card across main + sideboard combined (CR 903.5)
  - [ ] Banned list check on all cards in main + sideboard
- [ ] Match completion: when a player reaches `best_of // 2 + 1` wins, match status becomes "completed" with winner
- [ ] Game completion hook: when a game ends via `DELETE /game/{id}`, the result is recorded in the parent match's `games_won` counter
- [ ] >= 6 tests covering: match creation, sideboard swap validation (legal), sideboard swap validation (illegal count), singleton enforcement across main+side, next-game creation with updated decks, match completion at 2-0 and 2-1

**Dependencies**: None (independent of multiplayer work; can be used with 2-player games)

**Priority: Medium** — Competitive feature; not needed for single-game functionality

**Estimated Effort**: 4-6 hours

---

### SD-05: Multiplayer State-Based Actions and Win/Loss Conditions

**User Story**
As a player in a multiplayer game, I want the engine to correctly detect win and loss conditions so that games end properly with multiple players.

**Context**
In 2-player games, one player's loss is the other's win. In multiplayer:
- A player losing removes them from the game but does NOT make their opponents win (CR 104.3a)
- The game continues until only one player remains (or a specific win condition is met, like controlling the Emrakul)
- State-based actions must check all players' life totals, poison counters, and other loss conditions each time priority would be given

**Acceptance Criteria**
- [ ] State-based action checker (`check_state_based_actions` or equivalent) evaluates ALL players:
  - [ ] Player with life <= 0 loses (CR 104.3b)
  - [ ] Player with 10+ poison counters loses (CR 104.3c)
  - [ ] Player drawing from empty library loses (milling, CR 104.3d)
- [ ] When a player loses in multiplayer:
  - [ ] All permanents owned by that player leave the battlefield (CR 104.4a)
  - [ ] All spells owned by that player on the stack are removed (CR 104.4b)
  - [ ] The player is removed from `turn_order` — their turns are skipped going forward
  - [ ] Game continues with remaining players
- [ ] Game ends when only one player remains:
  - [ ] Last player standing is declared winner
  - [ ] `GameState.is_game_over = True`, `winner` set to last player's name
- [ ] Commander-specific loss conditions still apply (21+ commander damage from single commander, CR 903.10a)
- [ ] >= 5 tests covering: one player loses → game continues with remaining players, last player standing wins, all permanents of losing player removed, spells of losing player removed from stack, turn order updated to skip eliminated player

**Dependencies**: SD-01 (requires multiplayer game state and turn order)

**Priority: Medium** — Required for correct multiplayer gameplay but can be implemented after basic combat works

**Estimated Effort**: 2-3 hours

---

## Sprint D Dependencies Map

```
SD-01 (Game Creation + Turn Order) ──┬──→ SD-02 (Multiplayer Combat)
                                     │            ↓
                                     │       SD-05 (SBA + Win/Loss)
                                     │
                                     ├──→ SD-03 (Targeting + Spells)
                                     │
SD-04 (Sideboarding/Match System)    │      independent of multiplayer stories
```

## Sprint D Summary

| # | Story | Priority | Effort | Dependencies |
|---|-------|----------|--------|--------------|
| SD-01 | Multiplayer game creation + turn order | High | 4-6h | none |
| SD-02 | Multiplayer combat resolution | High | 4-6h | SD-01 |
| SD-03 | Multiplayer targeting + spells | Medium | 2-4h | SD-01 |
| SD-04 | Sideboarding + BO3 match system | Medium | 4-6h | none |
| SD-05 | Multiplayer SBA + win/loss | Medium | 2-3h | SD-01 |

**Total estimated effort**: 16-25 hours
